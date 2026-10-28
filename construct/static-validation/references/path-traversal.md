# path-traversal: Path traversal / arbitrary file access

## Claim to verify
An attacker-controlled path segment (`../`, absolute path, symlink, archive entry name) makes a
filesystem operation read, write, or delete outside the intended directory.

## Refute if
- The final path is resolved (`realpath`, `Path.resolve()`, `getCanonicalPath`,
  `Path.GetFullPath`, `filepath.Abs`+`Clean`) and checked to be inside the base directory
  (prefix check **with** trailing separator, or `is_relative_to`, `filepath.Rel` without `..`).
- The input is reduced to a bare name (`basename`, `secure_filename`, `Path.GetFileName`) or
  matched against an allowlist / regex such as `^[a-zA-Z0-9_-]+\.pdf$`.
- The filename is server-generated (UUID) and the user value is only a lookup key.
- The framework's safe helper is used correctly: Flask `send_from_directory` with a fixed
  directory, `safe_join`, Go `os.Root` / `http.Dir`, Express `res.sendFile(name, { root })`
  (still check for absolute paths and Windows separators).

## Framework protections to check
- `os.path.join(base, x)` / `path.join` / `Path.Combine` / `Paths.get(base, x)`: an absolute `x`
  replaces `base` in Python, .NET and Java; `path.join` normalises but does not contain.
- String replace of `../` is bypassable (`....//`, URL-encoded `%2e%2e%2f`, double decoding,
  backslashes on Windows).
- Prefix check without trailing separator: `/data/uploads-evil` passes `startswith("/data/uploads")`.
- Archive extraction: entry names in zip/tar (zip slip); Python `tarfile` before `filter="data"`.

## confirmed_static when
A cited request value reaches a cited filesystem call, the operation is reachable, and no
containment or allowlist exists on the path.

## Common false positives
- Values constrained by the router (`<int:id>`), or by an enum.
- Reads restricted to a directory of public static assets with no sensitive files and no write.

## Severity
Arbitrary read of server files (secrets, source) or arbitrary write: `high`/`critical`.
Read confined to another user's uploads: treat as `idor`-like `medium`/`high`.

## Remediation
Resolve the path and verify containment, or map user input to server-generated names.
