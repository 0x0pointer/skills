---
name: poc-authoring
description: Prove one statically validated hypothesis against the running PR app with a declarative, replayable poc.yaml - HTTP steps as named users, extracted variables, benign canaries (echoed token, canary URL, sentinel file) and oracles - validated and run with prsec-poc, then reported as the dynamic stage JSON. One reference per bug class (sqli, idor, bfla, ssrf, path-traversal, cmdi, xss, business-logic invariants).
---

# Writing a replayable PoC

You have one hypothesis that survived static validation and a running copy of the PR's app.
Your job is to write a **PoC file** that proves it through a real entry point. You do not decide
whether the bug is real: an agent-free replay runs your PoC in fresh environments on the PR
head (and on the base commit), and only its result counts. A PoC that only works because of
something you did by hand, or that fires on safe code, is worse than none.

## Inputs

- `hypothesis.json` and `static_verify.json`: the claim, entry point, source, sink, guards and
  the static reasoning. Start from the entry point and payload they describe.
- `envspec.json`: how the app is started (seeded users are listed in the env notes or visible in
  the `build` commands); `code_slices.md`, `pr.json`, `diff.patch`, and the repository.
- The app dir (`/work/app`) with a writable copy of the source in `/work/app/src`.

## Tools

```bash
prsec-env up                                    # install, build, start, wait for health
prsec-env status ; prsec-env logs -n 100        # is it up, what did it log
prsec-env reset                                 # fresh copy, clean state, start again
prsec-http --user alice --login-from poc.yaml GET /api/orders     # one request as a PoC user
prsec-canary new                                # print canary values for manual exploration
prsec-canary hits --contains <token>            # what the sink recorded
prsec-poc validate poc.yaml                     # schema check
prsec-poc run poc.yaml                          # run exactly like the replay; prints oracle results
```

## Method

1. **Bring the app up.** `prsec-env up`. If it fails, read the log and fix commands, env or stubs
   with the [env-building](../env-building/SKILL.md) skill (you may not change services). If it
   cannot be made to start, stop with outcome `env_failed`.
2. **Explore as a user.** Write the `users` section first (see
   [mocking](../mocking/SKILL.md) for seeded users), then use `prsec-http` to log in and call
   the entry point with a harmless value. Confirm the route exists, what it returns, and which
   ids and fields you need.
3. **Write the PoC** from the reference for the bug class (table below). Every value the attack
   needs comes from the PoC itself: seeded credentials in `vars`, ids via `extract`, payload
   markers via `${CANARY.*}`.
4. **Choose oracles** with the [oracles](../oracles/SKILL.md) skill: they must fire only when the
   bug is exploited and never on fixed code. Add a negative control.
5. **Validate and run.** `prsec-poc validate poc.yaml`, then `prsec-poc run poc.yaml`. Read the
   step records and oracle details, adjust, repeat.
6. **Prove it from clean state.** `prsec-env reset`, then `prsec-poc run poc.yaml` once more. It
   must fire without anything you did earlier in the session. Run it a second time to check
   it does not depend on order or leftovers (a replay runs once per fresh environment).
7. **Report** the dynamic stage JSON (below).

Budget: if the PoC still does not fire after a few honest variations of the payload the static
stage described, report `not_reproduced` with what you tried and what the app did. Absence of
proof is not proof of absence; the static label stays.

## The PoC file

Fields (YAML or JSON):

| Field | Meaning |
|---|---|
| `kind` | `http` (steps against the running app). `script` only when the code has no HTTP entry point: a `script` PoC is a direct call into code and is capped at `likely`. Its oracles read the script's stdout as step `script` (status 200 when it exits 0, else 500) |
| `hypothesis_id` | the hypothesis id (`H1`) |
| `description` | one or two sentences: who does what, and what proves it |
| `users.<name>` | `vars` (credentials, known ids), `headers` sent on every request as that user, `login` steps run before `steps`; cookies are kept per user |
| `steps[]` | `name` (unique across `steps` and every user's `login`, `[A-Za-z][A-Za-z0-9_-]*`, not `script`), `as` (user), `method`, `path` (a path on the app, or an absolute `http://<service>:<port>/...` URL to one of the EnvSpec's services, e.g. the oauth2 mock for a token or mailpit's API for a reset mail; every other absolute URL is refused. Redirects are not followed: a `302` is the step's response, so its `Location` can be checked), `parallel` (send the request N times at the same moment, 2-50, for race conditions; no `extract`; its oracles pass if any response matches), `headers`, `query`, at most one of `json` / `form` / `body`, `expect_status` (abort the run, not fired, if the status differs), `extract` |
| `extract.<var>` | exactly one of `json` (dotted path `items.0.id`), `header`, `regex` (group 1); sets `${USER.<var>}` for the step's user, `${USERS.<user>.<var>}` and `${VARS.<var>}` |
| `oracles[]` | 1-10 of `response_contains`, `response_regex`, `response_status`, `response_header`, `json_compare`, `canary_hit`, `command` (see the oracles skill) |
| `fires_when` | `all` (default, prefer it) or `any` |

Placeholders, substituted at run time in every string (not in `method`):

| Placeholder | Value |
|---|---|
| `${CANARY.token}` | fresh random letters+digits per run |
| `${CANARY.host}` / `${CANARY.url}` | `<token>.canary.invalid` / `http://<token>.canary.invalid/<token>`; resolves to the sink, which records the request |
| `${CANARY.file}` / `${CANARY.file_content}` | absolute path of a sentinel file created before the app starts / its secret content |
| `${USER.x}`, `${USERS.bob.x}`, `${VARS.x}` | user vars and extracted values |
| `${BASE_URL}` | `http://127.0.0.1:<port>` |

Quote placeholders inside YAML flow mappings: `{username: "${USER.username}"}`.

## Rules

- **Benign canaries only.** Prove command execution by echoing the canary token, SSRF by
  fetching `${CANARY.url}`, file reads by returning `${CANARY.file_content}`, injection by
  reading a marker the database builds. Change only objects the PoC or the seed created,
  never open a shell or a connection back to a listener, never exhaust resources.
- **Real entry point.** `kind: http` through the route an attacker would use, with the
  privileges the hypothesis' attacker has (an anonymous attacker gets no login).
- **Self-contained.** No ids, cookies or data from your manual exploration; extract them.
- **Same attacker, same input as the claim.** Do not prove a different, easier bug; if you find
  one, describe it in `reasoning` and keep the outcome about this hypothesis.

## Per bug class

References: `references/<class>.md` for sqli, idor, bfla, ssrf, path-traversal, cmdi, xss,
open-redirect, cors, cookie-flags, race-condition and business-logic.

| bug_class | Reference |
|---|---|
| `sqli` | [references/sqli.md](references/sqli.md) |
| `idor` | [references/idor.md](references/idor.md) |
| `bfla` | [references/bfla.md](references/bfla.md) |
| `ssrf` | [references/ssrf.md](references/ssrf.md) |
| `path-traversal` | [references/path-traversal.md](references/path-traversal.md) |
| `cmdi` | [references/cmdi.md](references/cmdi.md) |
| `xss` | [references/xss.md](references/xss.md) |
| `value-tampering`, `workflow-bypass`, `mass-assignment`, `race-condition` | [references/business-logic.md](references/business-logic.md) |

Other classes: same method; pick an effect that only the exploit produces and an oracle that
observes it.

## Output (dynamic stage JSON)

| outcome | When |
|---|---|
| `reproduced` | `prsec-poc run` fired from a clean state (after `prsec-env reset`); `poc` is required |
| `not_reproduced` | the app ran, the entry point was exercised, no PoC fired |
| `env_failed` | the app could not be started |
| `blocked` | proving it needs something the environment cannot provide (real IdP tokens, a hardware device, a paid third party whose response decides the bug) |

```json
{
  "hypothesis_id": "H1",
  "outcome": "reproduced",
  "reasoning": "Seeded alice and bob (build step init_db.py). bob lists his orders to get an id and note; alice's own list does not contain that note (control), but GET /api/orders/<bob's id> as alice returns 200 with it. Fired twice after prsec-env reset.",
  "poc": {
    "kind": "http",
    "hypothesis_id": "H1",
    "description": "alice reads bob's order through the new detail endpoint.",
    "users": {
      "alice": {"vars": {"username": "alice", "password": "alice-dev-pw"},
                "login": [{"name": "alice_login", "method": "POST", "path": "/api/login",
                           "json": {"username": "${USER.username}", "password": "${USER.password}"}, "expect_status": [200]}]},
      "bob": {"vars": {"username": "bob", "password": "bob-dev-pw"},
              "login": [{"name": "bob_login", "method": "POST", "path": "/api/login",
                         "json": {"username": "${USER.username}", "password": "${USER.password}"}, "expect_status": [200]}]}
    },
    "steps": [
      {"name": "bob_list", "as": "bob", "path": "/api/orders", "expect_status": [200],
       "extract": {"order_id": {"json": "0.id"}, "note": {"json": "0.note"}}},
      {"name": "alice_list", "as": "alice", "path": "/api/orders", "expect_status": [200]},
      {"name": "alice_reads_bob", "as": "alice", "path": "/api/orders/${USERS.bob.order_id}"}
    ],
    "oracles": [
      {"type": "response_contains", "step": "alice_list", "value": "${USERS.bob.note}", "negate": true},
      {"type": "response_status", "step": "alice_reads_bob", "status": [200]},
      {"type": "response_contains", "step": "alice_reads_bob", "value": "${USERS.bob.note}"}
    ],
    "fires_when": "all"
  },
  "envspec": null
}
```

Set `envspec` to the full corrected spec only when you changed commands, env or stubs to make the
app run; otherwise `null`.
