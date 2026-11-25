Verdict: fail

Blocking findings: shell command injection in git invocation; invalid paths are not rejected before git runs; count 0/negative is accepted instead of rejected; output format does not match the accepted contract.

Contents of `/tmp/fabro/security-review.md`:

```markdown
# Security Review

## Summary

- Verdict: fail.
- Findings by severity: 4 blocking, 0 non-blocking.
- Reviewed the full diff, review brief, issue, and approved spec. `scripts/skill_history.py` is a new HIGH-risk CLI because command-line input reaches a git invocation.
- Spec compliance: 2 of 4 acceptance criteria are met (`-n 3` is wired to `git log -n 3` for the exact documented argument shape, and no other files changed). AC1 output format and AC3 invalid-path behavior are not met; the specified count edge case is also not met.

## Changed files

| File | Risk | Blast radius |
| --- | --- | --- |
| `scripts/skill_history.py` | HIGH | Low: new maintainer CLI; `history()` is called only by `main()` in the new file, and grep found no repository callers outside this change. |

## Findings

### Blocking: shell command injection in git invocation

- File/line: `scripts/skill_history.py:7`
- Attacker model: a malicious PR/issue author or automation input source that can cause a maintainer/agent to run the CLI with attacker-controlled `PATH` or `-n` value.
- Reachable path: `__main__` passes `sys.argv[1:]` to `main()`, `main()` passes `argv[2]` and `path` to `history()`, and `history()` concatenates both into `os.popen(...)`, which runs through a shell.
- Example path checked: `python3 scripts/skill_history.py scripts/skill_history.py -n '1; touch /tmp/pwn; #'` would append a second shell command after `git log -n 1`.
- Exploitability: easy if untrusted CLI arguments are passed to the script. Impact is arbitrary command execution with the privileges and repository context of the script user.
- Required fix: replace `os.popen`/string concatenation with `subprocess.run([...], shell=False, ...)` and pass `git`, `log`, `-n`, the validated count, `--format=%h %an %s`, `--`, and the validated path as separate arguments.

### Blocking: invalid paths are not rejected before git runs

- File/line: `scripts/skill_history.py:13`
- Problem: `main()` only checks `os.path.exists(path)`. An existing path outside the repository, such as `/tmp`, reaches `git log`, returns status 0 from the Python script, and emits git's fatal message; the spec requires status 2, a stderr message, and no git command. A nonexistent path returns 2 but prints the message on stdout, not stderr.
- Required fix: resolve the repository root without running git for the invalid-path case, resolve the requested path, require that it exists and is within the repository, and print validation errors to `sys.stderr` before returning 2.

### Blocking: count 0/negative is accepted instead of rejected

- File/line: `scripts/skill_history.py:12`
- Problem: the count is taken as an unchecked string from `argv[2]`. `python3 scripts/skill_history.py scripts/skill_history.py -n 0` exits 0 and runs git, and negative/non-integer values are not rejected before reaching the git command. The spec requires count 0 or negative to exit 2.
- Required fix: parse the optional `-n COUNT` argument, convert `COUNT` to an integer, require it to be positive, and return 2 with a stderr message before calling `history()` for invalid counts.

### Blocking: output format does not match the accepted contract

- File/line: `scripts/skill_history.py:7`
- Problem: the git format string is `--format=%h_%an_%s`, but the spec's required output format is `git log --format=%h %an %s` (short hash, author, subject separated by spaces). `print(history(...))` also adds an extra blank line after git's output.
- Required fix: use `--format=%h %an %s` and write the captured output without appending an additional newline, or stream git stdout directly.

## Test coverage gaps

- No `test/` or `tests/` directory was found, and the spec says tests are not required.
- There is no automated coverage for the security-negative cases that failed review: shell metacharacters in `PATH`/count, existing paths outside the repository, nonexistent paths writing to stderr, and count `0`/negative returning status 2.

## What I did not cover

- I did not run the full test suite; the prompt stated protected checks already passed and asked for targeted review.
- I did not audit unchanged repository code beyond one caller/reference search for the new script.
- The file is new, so I skipped git blame and history for removed code as instructed.
```