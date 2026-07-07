"""Tool-enabled claude backend for skill-training.

Subclasses skillopt-sleep's ClaudeCliBackend so the ROLLOUT (running the skill)
executes with tools ENABLED — built-in Bash/Read/Edit plus the reused
agent-smith `pentest-agent` MCP server (session/http/kali/scan/report) — instead
of the stock tool-disabled call. This lets AGENTIC skills (threat-modeling,
api-security, …) actually produce their tool-driven output so the loop can
optimize them.

Design: only `attempt` / `attempt_with_tools` (the rollout) get tools. `_call`
is left inherited (tool-disabled, text mode) so the judge/reflect reasoning
calls stay lean and never spawn the MCP server.

Injected via a one-line monkeypatch — see tools_runner.py:
    skillopt_sleep.backend.ClaudeCliBackend = ToolEnabledClaudeCliBackend

Tunables (env):
  AGENT_SMITH_DIR        path to the agent-smith repo (the MCP server)   [default: known path]
  SKILLOPT_TOOLS_MCP     "0" to disable the pentest-agent MCP server (built-ins only)  [default: on]
  SKILLOPT_TOOLS_BUILTIN comma list of built-in tools to allow           [default: Bash,Read,Edit]
  PENTEST_TARGET_PATH    optional local path for scan(semgrep|trufflehog) mounts
"""
import json
import os
import shutil
import subprocess
import tempfile
from typing import List, Tuple

from skillopt_sleep.backend import ClaudeCliBackend, skill_hash

AGENT_SMITH_DIR = os.environ.get(
    "AGENT_SMITH_DIR", "/Users/gibson/Desktop/development/agent-smith"
)
MCP_SERVER = "pentest-agent"
ENABLE_MCP = os.environ.get("SKILLOPT_TOOLS_MCP", "1") != "0"
BUILTIN_TOOLS = os.environ.get("SKILLOPT_TOOLS_BUILTIN", "Bash,Read,Edit")

_MCP_CONFIG_PATH = ""


def _mcp_config_path() -> str:
    """Write (once) an mcp-config that spawns the agent-smith pentest-agent
    server over stdio, and return its path."""
    global _MCP_CONFIG_PATH
    if _MCP_CONFIG_PATH and os.path.exists(_MCP_CONFIG_PATH):
        return _MCP_CONFIG_PATH
    py = os.path.join(AGENT_SMITH_DIR, ".venv", "bin", "python")
    if not os.path.exists(py):
        py = "python3"
    env = {"PYTHONPATH": AGENT_SMITH_DIR}
    if os.environ.get("PENTEST_TARGET_PATH"):
        env["PENTEST_TARGET_PATH"] = os.environ["PENTEST_TARGET_PATH"]
    cfg = {"mcpServers": {MCP_SERVER: {
        "command": py, "args": ["-m", "mcp_server"], "cwd": AGENT_SMITH_DIR, "env": env,
    }}}
    path = os.path.join(tempfile.gettempdir(), "skillopt_tools_mcp.json")
    with open(path, "w") as f:
        json.dump(cfg, f)
    _MCP_CONFIG_PATH = path
    return path


def _allowed_tools() -> str:
    tools = [t for t in BUILTIN_TOOLS.split(",") if t]
    if ENABLE_MCP:
        tools.append(f"mcp__{MCP_SERVER}")
    return ",".join(tools)


def _classify_blocks(content):
    """Yield ('tool', name) / ('text', str) for each content block of an assistant message."""
    for b in content or []:
        if b.get("type") == "tool_use":
            name = b.get("name", "")
            if name.startswith(f"mcp__{MCP_SERVER}__"):
                name = name.split("__", 2)[2]  # mcp__pentest-agent__report -> report
            yield "tool", name
        elif b.get("type") == "text":
            yield "text", b.get("text", "")


def _parse_stream(stdout: str) -> Tuple[str, List[str]]:
    """Parse `claude --output-format stream-json` output into (final_text, tool_names)."""
    final, texts, called = "", [], []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") == "assistant":
            for kind, val in _classify_blocks(ev.get("message", {}).get("content", [])):
                (called if kind == "tool" else texts).append(val)
        elif ev.get("type") == "result" and ev.get("subtype") == "success":
            final = ev.get("result", "") or ""
    final = final or "\n".join(t for t in texts if t)
    seen: set = set()
    uniq = [c for c in called if c and not (c in seen or seen.add(c))]
    return final.strip(), uniq


class ToolEnabledClaudeCliBackend(ClaudeCliBackend):
    name = "claude-tools"

    def __init__(self, model: str = "", claude_path: str = "claude", timeout: int | None = None):
        # Agentic rollouts (spawn MCP server + several tool calls) are much
        # slower than a single text turn, so default the per-rollout cap higher
        # than the stock 180s. Override with SKILLOPT_TOOLS_TIMEOUT.
        if timeout is None:
            timeout = int(os.environ.get("SKILLOPT_TOOLS_TIMEOUT", "600"))
        super().__init__(model=model, claude_path=claude_path, timeout=timeout)

    def _run(self, prompt: str) -> Tuple[str, List[str]]:
        cmd = [self.claude_path, "-p", "--output-format", "stream-json", "--verbose"]
        if os.environ.get("ANTHROPIC_API_KEY"):
            cmd.append("--bare")  # API-key auth; MCP + Bash/Read/Edit still load under --bare
        cmd += [
            "--disable-slash-commands",
            "--exclude-dynamic-system-prompt-sections",
            "--allowedTools", _allowed_tools(),
            "--permission-mode", "dontAsk",
        ]
        if ENABLE_MCP:
            cmd += ["--mcp-config", _mcp_config_path(), "--strict-mcp-config"]
        if self.model:
            cmd += ["--model", self.model]
        cmd += ["--", prompt]
        # SKILLOPT_TOOLS_CWD lets the rollout read a real codebase (e.g. a review
        # target) with the built-in Read/Bash tools. Otherwise use a throwaway dir.
        persistent = os.environ.get("SKILLOPT_TOOLS_CWD", "")
        if persistent:
            cwd, cleanup = os.path.abspath(persistent), False
        else:
            cwd, cleanup = tempfile.mkdtemp(prefix="skillopt_tools_"), True
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout, cwd=cwd
            )
        except Exception:
            return "", []
        finally:
            if cleanup:
                shutil.rmtree(cwd, ignore_errors=True)
        text, called = _parse_stream(proc.stdout or "")
        self._detect_cli_error(text, proc.stderr or "")
        return text, called

    # rollout with tools (generic mined/authored tasks) --------------------
    def attempt(self, task, skill: str, memory: str, sample_id: int = 0) -> str:
        if getattr(task, "system", ""):
            # research-benchmark tasks carry their own system prompt: defer to
            # the stock (tool-disabled) path.
            return super().attempt(task, skill, memory, sample_id)
        prompt = (
            "Complete the following task for the user. Follow the skill and memory "
            "guidance below EXACTLY, including any tool-use, output-format and length "
            "requirements. You have REAL tools available — when the skill instructs "
            "you to call a tool (e.g. session(), report(), http(), scan()), actually "
            "call it. When a 'Learned preferences' rule sets an explicit limit, prefer "
            "it over more general advice it refines. Always produce the complete "
            "analysis/output as your final message — never an empty or stub response.\n\n"
            f"# Skill\n{skill or '(none)'}\n\n# Memory\n{memory or '(none)'}\n\n"
            f"# Task\n{task.intent}\n\n{task.context_excerpt}\n\n"
            "Return the final answer text."
        )
        salt = f"s{sample_id}:" if sample_id else ""
        key = "attempt:" + salt + skill_hash(prompt)
        if key in self._cache:
            return self._cache[key]
        text, _called = self._run(prompt)
        self._tokens += len(prompt) // 4 + len(text) // 4
        self._cache[key] = text
        return text

    # rollout with tools + real tool-call capture (tasks with tool_called checks)
    def attempt_with_tools(self, task, skill: str, memory: str, tools) -> Tuple[str, List[str]]:
        prompt = (
            "Complete the following task. Follow the skill and memory guidance "
            "EXACTLY, including any tool-use requirement. You have REAL tools "
            "available; when the skill says to use a tool, you MUST actually call it. "
            "Treat a 'Learned preferences' block as hard constraints.\n\n"
            f"# Skill\n{skill or '(none)'}\n\n# Memory\n{memory or '(none)'}\n\n"
            f"# Task\n{task.intent}\n\n{task.context_excerpt}\n\n"
            "Return the final answer text."
        )
        text, called = self._run(prompt)
        self._tokens += len(prompt) // 4 + len(text) // 4
        called_lower = {c.lower() for c in called}
        matched = [t for t in (tools or []) if str(t).lower() in called_lower]
        return text, matched
