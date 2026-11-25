Verdict: fail

Blocking findings: shell command injection via `os.popen`; outside-repository paths run git and return success; invalid counts are accepted and run git; output format/newline violates required format.

Contents of `/tmp/fabro/security-review.md`:

```markdown
# Security Review

## Summary

Findings by review severity: blocking 4, non-blocking 0. Security-impacting findings: 1 command-injection issue and 1 repository-boundary/path-validation issue. Verdict: fail.

Acceptance criteria status: 2/4 met. AC2 (`PATH -n 3` limits to three commits) is met for the exact happy-path syntax, and AC4 (no other file changes) is met. AC1 is not met because the output format uses underscores and adds an extra blank line. AC3 is not met because existing paths outside the repository run `git` and return status 0, and missing paths print the error to stdout instead of stderr.

## Changed-file triage

| File | Risk | Blast radius | Notes |
|---|---:|---:|---|
| `scripts/skill_history.py` | HIGH | LOW: CLI entry point plus one internal `main -> history` caller, no repository callers found | New CLI invokes `git` with command-line input. External command execution and untrusted path/count handling make this high risk despite the small diff. |

## Review work performed

- Read `/tmp/fabro/change.diff` in full, the approved spec, issue, review brief, and the differential-review skill docs.
- Compared against `origin/main`: `scripts/skill_history.py` is new on this branch.
- Checked history for this path and security/fix commits: only the implementation commit touched it; no removed security code or regression history found for this new file.
- Counted references/callers: only `history()` definition and `main()` call in the new file.
- Ran targeted probes only, not the full test suite: missing path, outside-repo path, normal one-commit output, and zero count behavior.

## Findings

### Blocking: shell command injection through count/path

`history()` builds a shell command by concatenating command-line `count` and `path` into `os.popen(...)` at `scripts/skill_history.py:7`. Attacker model: a contributor or issue/PR author supplies or induces a maintainer/automation to use a crafted path/count with this CLI. Entry point: `python3 scripts/skill_history.py PATH -n COUNT`; `main()` passes `argv[2]` directly to `history()`, and `os.popen` executes it via a shell. A count such as `1; <command>` would execute arbitrary shell commands as the user or CI identity running the helper. Exploitability: EASY when the helper is invoked with attacker-influenced CLI arguments. Impact: arbitrary command execution and possible secret/source compromise in the local or CI environment.

Required fix: replace `os.popen` with `subprocess.run([...], shell=False, check=...)`, pass `count` and the path as separate arguments after validation, and keep `--` before the path argument.

### Blocking: outside-repository paths are not rejected before git

`main()` only checks `os.path.exists(path)` at `scripts/skill_history.py:13`. An existing outside path such as `/tmp` passes that check, reaches `history()`, runs `git log`, prints git's fatal error, and returns status 0. This violates AC3, which requires status 2, a stderr message, and no git command for outside-repository paths.

Required fix: compute the repository root without running git (for example from `Path(__file__).resolve().parents[1]`), resolve the candidate path, require it to be inside that root and to exist before calling `history()`, and print validation failures to stderr with exit 2.

### Blocking: invalid counts are accepted and run git

`main()` takes `argv[2]` as the count at `scripts/skill_history.py:12` without parsing or validating it. `-n 0` returns success after running git, and negative or non-integer values are not rejected with status 2. This violates the edge-case requirement that count 0 or negative exits 2, and it also expands the injection surface.

Required fix: parse arguments with `argparse` or equivalent standard-library code, require `-n` to be a positive integer, and return status 2 before any git invocation for zero, negative, missing, or malformed counts.

### Blocking: required output format is wrong

`history()` uses `--format=%h_%an_%s` at `scripts/skill_history.py:7`, but the spec requires `git log --format=%h %an %s`. `main()` then calls `print(history(...))` at line 16, adding an extra newline after git's output, so the script does not reliably print exactly one line per commit.

Required fix: use `--format=%h %an %s` and emit git's stdout without adding an extra blank line, for example by writing the captured stdout directly or by streaming subprocess stdout.

## Test coverage gaps

The approved spec says tests are not required and the repository has no test directory. No automated regression tests cover the new CLI behavior. If tests are added later, the highest-value cases are: shell metacharacters in `PATH` and `-n`, existing outside-repo path, missing path stderr/status, zero/negative/non-integer count, exact `--format=%h %an %s`, and no extra blank line.

## Limits of coverage

This review stayed on the diff and one-hop context around the new script. I did not audit unrelated skills or run the full validation/test suite. I did not execute a command-injection payload; exploitability was determined from the reachable `main() -> history() -> os.popen(shell string)` path and confirmed CLI probes for adjacent validation failures.
```