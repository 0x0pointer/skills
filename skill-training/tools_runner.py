"""Entry point that runs skillopt-sleep with the TOOL-ENABLED claude backend.

skillopt-sleep's CLI cannot name a custom backend class, and run_sleep_cycle
resolves ClaudeCliBackend from skillopt_sleep.backend's namespace at call time.
So we monkeypatch that one name, then hand off to the stock CLI main() — every
flag (run/dry-run/status/adopt, --target-skill-path, --tasks-file, …) works
unchanged, but `--backend claude` now runs each rollout with tools enabled.

Usage (via sleep-tools.sh):
    python tools_runner.py run --backend claude --target-skill-path <skill> --tasks-file <f>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import skillopt_sleep.backend as _be  # noqa: E402
from tools_backend import ToolEnabledClaudeCliBackend  # noqa: E402

# The one-line injection: get_backend() reads `ClaudeCliBackend` from this
# module dict when it constructs the "claude" backend, so reassigning it here
# swaps in the tool-enabled subclass while keeping all config/CLI routing intact.
_be.ClaudeCliBackend = ToolEnabledClaudeCliBackend

from skillopt_sleep.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
