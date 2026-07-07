# vuln-flask — intentionally vulnerable test fixture

A tiny, self-contained Flask app used to score the `codebase` skill in the
tool-enabled training loop. **Not a real service — do not deploy.**

Planted vulnerabilities (the `codebase` review should find these):

| # | Vulnerability | Location | ASVS |
|---|---|---|---|
| 1 | Hardcoded secret | `SECRET_KEY` | V13 config/secrets |
| 2 | SQL injection | `/user` (`id`) | V2 |
| 3 | OS command injection | `/ping` (`host`) | V2 |
| 4 | Path traversal | `/download` (`file`) | V2 |
| 5 | Weak/unsalted hashing (MD5) | `hash_password` | V11 crypto |
| 6 | Debug mode in production | `app.run(debug=True)` | V16 |

Used by `skill-training/tasks/codebase.json`. The rollout runs with its working
directory set to this folder (`SKILLOPT_TOOLS_CWD`), so the skill reads these
files with the built-in Read/Bash tools. For a larger, realistic target see
`skill-training/tasks/codebase-vuln-bank.json` (points at the cloned vuln-bank).
