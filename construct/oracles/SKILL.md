---
name: oracles
description: Choose PoC oracles that fire only when the vulnerability is exploited - canary-derived values that cannot appear by accident, values the vulnerable code must compute, invariants read back from persisted state, negative controls - and check that the PoC cannot fire on fixed or base code. The replay's oracle results are the evidence; the agent's own judgement never is. Used by the dynamic stage with poc-authoring.
---

# Oracles that cannot fire by accident

An oracle is the machine-checked condition that decides whether a PoC **fired**. The agent-free
replay evaluates it, several times, on the PR head and on the base commit. A label of
`reproduced` rests entirely on it, so an oracle that can pass on safe code turns a guess into a
false "proven" finding, the most expensive mistake this pipeline can make.

## The test every oracle must pass

For each oracle, answer three questions, and rewrite it until all three are "no":

1. **Could it pass if the request were simply echoed back?** (error pages, search pages, JSON
   APIs that return the input, logs forwarded to an outside host)
2. **Could it pass on the fixed code?** Imagine the obvious fix (bound parameter, ownership
   filter, role check, `quantity >= 1` validation, allowlist). Would the oracle still pass?
3. **Could it pass on a fresh environment without the exploit?** (seed data that already
   contains the value, a status code every request gets, a sink hit the app makes at start-up)

If you cannot get all three to "no", the outcome is `not_reproduced`, with what you observed in
`reasoning`, not a weaker oracle.

## Oracle types and how to use them safely

| type | Fires when | Safe use | Unsafe use |
|---|---|---|---|
| `response_contains` | the step's response body contains `value` | a value the vulnerable code **computes** or **leaks**: `${CANARY.file_content}`, a DB-concatenated marker, another user's seeded or canary note | any string that is in the request (`${CANARY.token}` alone when the input is echoed) |
| `response_status` | the status is in `status` | a supporting condition next to a content oracle; the privileged call returned success | the only oracle (`500` happens for many reasons; `200` is returned for "nothing happened") |
| `response_regex` | the step's body matches `pattern` (Python regex, as written; a match that is in the request does not count) | a server-built shape: `prsec42[0-9a-f]{12}` from a concatenation, a stack trace line, an unescaped tag | broad patterns (`.*`, `error`) that match ordinary pages |
| `response_header` | header `name` (case-insensitive; every value checked, e.g. each `Set-Cookie`) is `present` / `absent` or `equals` / `contains` / `starts_with` / `regex` `value` | open redirect (`Location` `starts_with` `http://${CANARY.host}`), CORS (`Access-Control-Allow-Origin` `equals` the attacker origin you sent, plus `Allow-Credentials` `equals` `true`), cookie flags (`Set-Cookie` `regex` `^session=(?!.*HttpOnly)`), XSS content type (`Content-Type` `contains` `text/html`) | a header every response carries anyway, or a redirect to a URL you did not inject |
| `json_compare` | the value at `path` compares to `value` with `op` | an invariant on persisted, server-computed state read back in a later step (`total lt 0`, `role eq admin`) | fields copied from the request into the response without being stored |
| `canary_hit` | the sink recorded a request containing `value` | SSRF / outbound fetch to `${CANARY.url}` or `${CANARY.host}` | apps that already forward request bodies to outside hosts (check `prsec-canary hits` first) |
| `command` | stdout of `run` (in the app dir, after the steps) contains `expect` | inspecting state the app wrote (`cat /tmp/prsec-<token>`, a DB query through the app's tooling) | commands that create the expected output themselves |

`negate: true` on `response_contains` / `response_regex` / `command` inverts the check: use it for **controls**.

On a `parallel` step an oracle passes if **any** of its responses matches (a negated one: if
**none** does). For races, put the invariant on a later, single read step instead (`json_compare`
on the redeemed count or balance): that is what the race actually broke.

## Make values unique

- Every marker carries `${CANARY.token}`, which is fresh per run: it cannot be in seed data or
  left over from an earlier run.
- Make the vulnerable code **build** the marker from parts so that echoing the input cannot
  produce it: `'prs' || 'ec${CANARY.token}'` (SQL), `echo prsec$((6*7))${CANARY.token}` (shell).
- For data leaks, match a value only the victim has: B's seeded note, B's canary note, the
  sentinel file content. Never a field name, a generic word, or an id that every user has.
- Beware weak values. An `extract` that finds nothing, or finds `null` or an empty string,
  aborts the run (not fired), and an oracle whose value renders empty never passes. A value that
  is merely short or generic (`1`, `true`, `"null"`, a user id every response carries) still
  matches by accident: pair a `response_contains` on an extracted value with a negative control
  on a response that must **not** contain it.
- A `response_contains` value that occurs in the step's **own request** (path, query, headers,
  body) never passes: an echo or an error message that repeats the input proves nothing. Markup
  (a value with `<`, `>`, `&` or quotes) is the exception, since its unescaped reflection is the
  XSS proof.

## Negative controls

A control is a step plus an oracle that shows the effect is caused by the exploit, not by the
setup. Use `fires_when: all` so the control has to hold as well.

| bug | control |
|---|---|
| `idor` | A's own listing does not contain B's value (`negate: true`) |
| `bfla`, `mass-assignment` | the protected field has its original value before the exploit (`role eq user`) |
| `value-tampering`, `workflow-bypass` | the prerequisite really was not met (`paid eq false`) |
| injection | a request with the same parameter but a harmless value does not contain the marker (only needed when the marker could be ambiguous) |

## The PoC must not fire on fixed code

The base replay is an automatic control: on base the endpoint usually does not exist or the
behaviour differs, so a PoC that fires there is either a pre-existing bug (`introduced: false`)
or a bad oracle. Before you report `reproduced`, check the fixed code mentally against every
oracle (question 2 above). When the repository makes it cheap, check it for real: apply the
obvious fix to the writable copy in `/work/app/src`, restart the app, run the PoC and confirm it
does **not** fire. Then undo the fix and `prsec-env reset` before your final run; replays always
start from the unmodified PR source. Describe what you did in `reasoning`.

## Never rely on your own judgement

- Only `prsec-poc run` decides whether a PoC fired, and only the replay decides the label. Do
  not report `reproduced` because a response "looks vulnerable" or because a manual
  `prsec-http` request worked; encode that observation as an oracle and run it.
- Do not interpret error messages, stack traces or timing as proof unless an oracle captures a
  value only the exploit can produce.
- If the oracle result and your expectation disagree, believe the oracle and fix the PoC or
  report `not_reproduced`; never bend an oracle until it passes.

## Example: weak versus strong

Weak (fires on the fixed code, because the search page echoes `q`):

```yaml
kind: http
hypothesis_id: H1
description: Weak example - do not copy. The token is in the request and the page echoes it.
steps:
  - name: inject
    path: /api/orders/search
    query: {q: "' UNION SELECT 1, '${CANARY.token}', 0 -- "}
oracles:
  - type: response_contains
    step: inject
    value: ${CANARY.token}
```

Strong (only the database can produce `prsec<token>`, and the control proves the plain search
does not):

```yaml
kind: http
hypothesis_id: H1
description: The database concatenates a marker that a parameterised query can never return.
steps:
  - name: plain
    path: /api/orders/search
    query: {q: "prsec"}
    expect_status: [200]
  - name: inject
    path: /api/orders/search
    query: {q: "zz' UNION SELECT 1, 'prs' || 'ec${CANARY.token}', 0 -- "}
oracles:
  - type: response_contains
    step: plain
    value: prsec${CANARY.token}
    negate: true
  - type: response_contains
    step: inject
    value: prsec${CANARY.token}
fires_when: all
```
