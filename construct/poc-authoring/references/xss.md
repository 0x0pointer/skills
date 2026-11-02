# xss: proving cross-site scripting (server side)

## What proves it
An **HTML** response contains attacker markup unescaped in a context where the browser would
parse it. The replay has no browser, so the proof is the raw marker in the HTML: an element
whose name carries the canary token. Escaped output (`&lt;prsec...`) does not match.

## Payload
A harmless custom element: `<prsec${CANARY.token}>`. Adjust for the context:

| Context | Payload | Oracle value |
|---|---|---|
| HTML body | `<prsec${CANARY.token}>` | `<prsec${CANARY.token}>` |
| double-quoted attribute | `x"><prsec${CANARY.token}>` | `"><prsec${CANARY.token}>` |
| single-quoted attribute | `x'><prsec${CANARY.token}>` | `'><prsec${CANARY.token}>` |
| inside a script block | `</script><prsec${CANARY.token}>` | `</script><prsec${CANARY.token}>` |

```yaml
kind: http
hypothesis_id: H9
description: >
  The new search page renders q with Markup(), bypassing autoescaping. A custom element carrying
  the canary token comes back unescaped in the HTML.
steps:
  - name: reflect
    path: /search
    query:
      q: <prsec${CANARY.token}>
oracles:
  - type: response_status
    step: reflect
    status: [200]
  - type: response_header
    step: reflect
    name: Content-Type
    op: contains
    value: text/html
  - type: response_contains
    step: reflect
    value: <prsec${CANARY.token}>
```

## Stored XSS
One user stores the marker (comment, profile name), a **second** user views the page that
renders it; the oracle runs on the viewer's step.

## Pitfalls
- A JSON API echoing the marker is not XSS by itself (`application/json` is not rendered).
  Target the route that renders HTML and keep the `response_header` `Content-Type` `contains`
  `text/html` oracle: without it the PoC also fires on a JSON echo.
- Never use script payloads that call out, read cookies or do anything; the marker is enough.
- DOM-based XSS lives in client JavaScript and cannot be proven without a browser: report
  `blocked` unless the server reflects the payload.
