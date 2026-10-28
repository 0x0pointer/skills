# Known-safe wrappers

A wrapper belongs here only after AppSec has reviewed its implementation. Each entry states the
**bug class it neutralises**, the **conditions** under which it does, and what it does **not**
cover. Use canonical `bug_class` names from `bug-classes.yaml`.

| Wrapper (how it appears in code) | Neutralises | Conditions | Does not cover |
|---|---|---|---|
| TODO(appsec): e.g. `db.safe_query(sql, params)` | `sqli` | `sql` is a literal; values passed in `params` | identifiers (`ORDER BY`), `db.safe_query(f"...")` |
| TODO(appsec): e.g. `http.fetch_external(url)` | `ssrf` | default client; egress proxy enforces allowlist | `http.fetch_internal`, custom clients |
| TODO(appsec): e.g. `files.open_user_upload(user, name)` | `path-traversal`, `idor` | name passed as-is; wrapper resolves under the user's prefix | direct `open()` on the storage path |
| TODO(appsec): e.g. `render_safe_html(markdown)` | `xss` | output inserted as-is | values concatenated after sanitising |
| TODO(appsec): e.g. `money.Amount` type | `value-tampering` | constructed via `Amount.parse` (rejects negative, fixes scale) | raw `Decimal` arithmetic |

## Review notes

- TODO(appsec): link each wrapper to its source path and the review date, so stale entries can be
  re-checked when the wrapper changes.
