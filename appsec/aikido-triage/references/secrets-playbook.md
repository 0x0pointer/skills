# Application Secrets Playbook

Lazy-loaded reference for Phase 3 of `/aikido-triage` — covers the Application Secrets category (`issue_type` = `leaked_secret`). Populate the finding record defined in SKILL.md for every finding below.

---

## Step 1 — removal check

Before doing anything else, read `CODEBASE_PATH/<file>` at the flagged `line`. This is the cheapest possible check and it clears a large fraction of `leaked_secret` findings on repos with any churn — Aikido's feed lags behind the current HEAD, and a lot of "leaked secrets" are actually leaked-and-then-deleted secrets.

- If the file no longer exists at that path, **or** the line no longer contains anything resembling the flagged secret (the line was edited, the literal was replaced, the whole block was refactored away) → render the verdict immediately:
  - `technical_verdict: "CLOSE"`
  - `close_category: "File Removed"`
  - `evidence`: *"File does not exist at HEAD / line no longer matches. Finding references removed code."*
- **Stop here.** Do not proceed to Step 2 for a removed finding — there is nothing left to trace usage of, and no liveness probe is warranted for a literal that no longer exists in the tree (the credential may still be exposed in git history, but that is a separate, broader question this playbook does not attempt to answer from a single flagged line).

If the file exists and the line still contains the secret (or something that looks like it), continue to Step 2.

---

## Step 2 — static usage estimate

With the secret confirmed still present, the next question is not "is this secret real" but "is this secret still *live in a way that matters* — referenced by code that actually runs in production — or is it stale."

Grep the codebase for other live references to the same secret value, variable name, or config key. Sort what you find into three buckets:

- **(a) Referenced in active application code that runs in production** — imported/read by a service entrypoint, a request handler, a background worker, a deploy manifest that's actually applied. This is the strongest signal the secret matters.
- **(b) Only appears in test fixtures, example files, or archived/dead code** — `spec/`, `test/`, `fixtures/`, `examples/`, a module nothing imports, a branch/directory that's clearly retired. Weak or no signal.
- **(c) Appears superseded** — the same service now reads the equivalent value from an environment variable, secrets manager, or vault call elsewhere in the code, suggesting this hardcoded literal was rotated out but the old copy was never deleted. This is a specific and useful sub-case of "stale": it means someone already fixed the underlying problem, they just left the corpse behind.

**Label this explicitly as an estimate, not a fact.** You are inferring likely-live-vs-stale from code shape — imports, call sites, directory conventions — not confirming whether the credential itself is still valid on the provider's side. Write `verification_method` and `evidence` in a way that makes this clear, e.g. *"static usage estimate — referenced from `src/workers/billing.rb:42`, appears to be the live production path; not liveness-confirmed."* Never let this estimate get quietly reframed as a determination of liveness downstream — that distinction is the entire point of Step 3/4 existing.

### False-positive pattern table

Apply this table to the flagged line before concluding a secret is real. It is carried over from the prior version of this skill and is still correct — most `leaked_secret` volume clears here, before any usage estimate or liveness question is even relevant.

| What you see | Verdict |
|---|---|
| `ENV.fetch(...)`, `ENV[...]`, `ENV.fetch(..., nil)` | **CLOSE — False Positive** (env var read) |
| `${{ secrets.* }}` (GitHub Actions) | **CLOSE — False Positive** (GH Actions secret) |
| `${VARIABLE_NAME}` in `.npmrc`/`.env.example` | **CLOSE — False Positive** (env var placeholder) |
| `--mount=type=secret` in Dockerfile | **CLOSE — False Positive** (Docker build secret) |
| A long regex, UA string, or binary-looking data | **CLOSE — False Positive** (pattern mismatch) |
| An actual hardcoded token/key/password string | Continue to Step 3 |
| A real URL with embedded credentials (`user:pass@host`) | Continue to Step 3 |

For the `sidekiq-sensitive-url` rule specifically: check whether the flagged line is an actual Redis URL with embedded credentials, or just a gem declaration in `Gemfile`/`Gemfile.lock` — this rule fires on the gem name alone almost as often as on a real credential, and the `Gemfile`/`Gemfile.lock` case is almost always a false positive.

Anything that survives this table — a real hardcoded token, key, password, or credentialed URL — proceeds to Step 3.

---

## Step 3 — check Aikido's own liveness signal first

Before considering any probe of your own, check whether Aikido already answered the liveness question for you. Some `aikido_issues_list` results for `leaked_secret` issues carry a liveness/validity field alongside the standard fields — treat this as **available-when-relevant, not guaranteed present on every issue**; plenty of `leaked_secret` findings won't have it.

- If Aikido already reports the secret as **confirmed active** or **confirmed inactive/revoked**, trust it and cite it directly. Set `verification_method` to something like *"Aikido-reported liveness signal: confirmed active"* and move straight to Step 5 — do not re-probe something Aikido has already told you the answer to. Re-probing a credential Aikido already validated adds a needless real-world network call for no new information.
- Only proceed to Step 4 when **no such signal is present** on the issue.

---

## Step 4 — opt-in liveness probe (safety-critical — read this section in full)

**This is the single most safety-sensitive step in this entire skill. Liveness probing is opt-in only, every single time, with no exceptions.**

The skill must **never** automatically make an outbound network call using a discovered credential. It does not matter how confident the pattern match is, how trivial the check seems, or whether the provider is on the curated allowlist below — an allowlist entry means *a safe check exists*, it does not mean *permission to run it*. Permission comes from the user, fresh, every time. There is no "the user already said yes to a similar finding earlier in this run" — ask again for each finding.

The procedure:

1. Recognize the secret's format against the curated allowlist below (by prefix/shape — `AKIA`/`ASIA`, `ghp_`/`github_pat_`, `xoxb-`/`xoxp-`, `sk_live_`/`sk_test_`, `SG.`, a Twilio Account SID + Auth Token pair). If it doesn't match anything on the list, do not attempt a probe at all — skip straight to the fallback below.
2. If it matches, **stop and ask the user before doing anything else.** Name the provider, name the exact call you would make, state plainly that the call is read-only and non-mutating, and wait for an explicit yes. Use wording like this:

   > Found a hardcoded-looking **[Provider] key** at `file:line`. I can make one read-only identity check (`[exact call]`) to confirm whether it's still active — this makes a single authenticated, non-mutating network call using the discovered credential. Proceed? (yes/no)

3. If the user says yes, run exactly the named call — nothing broader, no exploration beyond the single identity/verification check named in the prompt.
4. If the user declines, or the provider isn't recognized or isn't on the allowlist, set `verification_method: "Unconfirmed — not probed"` and fall back entirely to the Step 2 static usage estimate for the verdict. **Never guess liveness.** A declined or unavailable probe is not evidence of anything — it just means Step 5 has to be decided without it.

### Curated allowlist — non-mutating identity checks only

Anything **not** on this table gets no probe attempt at all, ever — mark it unconfirmed and rely on the Step 2 estimate. This list only exists to make the *offer* precise when it's offered; it is not a general license to probe.

| Provider (key pattern) | Non-mutating check | How to call it |
|---|---|---|
| AWS access key (`AKIA...`/`ASIA...` + secret) | `sts:GetCallerIdentity` | Prefer the `aws` CLI via Bash: `AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... aws sts get-caller-identity` — do not hand-roll SigV4 HTTP signing |
| GitHub PAT / fine-grained token (`ghp_...`, `github_pat_...`) | `GET /user` | `curl -s -H "Authorization: Bearer <token>" https://api.github.com/user` |
| Slack token (`xoxb-...`, `xoxp-...`) | `auth.test` | `curl -s -X POST -H "Authorization: Bearer <token>" https://slack.com/api/auth.test` |
| Stripe secret key (`sk_live_...`/`sk_test_...`) | Read-only balance fetch | `curl -s -u <key>: https://api.stripe.com/v1/balance` |
| SendGrid API key (`SG....`) | Scopes check | `curl -s -H "Authorization: Bearer <key>" https://api.sendgrid.com/v3/scopes` |
| Twilio (Account SID + Auth Token) | Fetch account resource | `curl -s -u <sid>:<token> https://api.twilio.com/2010-04-01/Accounts/<sid>.json` |

A few notes that apply across every row above:

- Every listed call is read-only by design — no writes, no resource creation, no state changes on the provider side. Do not substitute a different endpoint for the same provider "because it's basically the same thing," even if it also looks read-only — use exactly the call named here (or named in the prompt you showed the user), nothing improvised.
- **A failed or expired-credential response is itself useful negative evidence.** A 401/403/"invalid token" response confirms the credential is inactive/revoked just as usefully as a 200 confirms it's active — record whichever outcome you actually got, don't treat a failure as "the probe didn't work, ignore it."
- Never log, print, or paste the full credential value into the finding record's `evidence` field — reference it by file:line and a truncated/masked form, and record only the *result* of the call (active / inactive / unconfirmed), not the raw request/response containing the secret.

---

## Step 5 — verdict

Combine the removal check (Step 1), the usage estimate (Step 2), and the liveness result if one was obtained (Step 3 or Step 4) into the finding record. Apply in this order:

- **Liveness confirmed active** (via Step 3's Aikido signal or a Step 4 probe that succeeded) → `technical_verdict: "KEEP OPEN"`, `close_category: "Real Finding"`, `exploitability_rating: "HIGH"`. An active credential in the codebase is a real, currently-exploitable exposure regardless of how it scores on the usage estimate — even a "stale-looking" reference is still live if the provider says so.
- **Liveness confirmed inactive/revoked** (via Step 3 or a Step 4 probe) **and** the Step 2 usage estimate is weak (bucket b or c — test fixture, dead code, or superseded by a rotated-in replacement) → likely `technical_verdict: "CLOSE"`, `close_category: "Not Exploitable"`, `exploitability_rating: "NOT EXPLOITABLE"`. Even so, if the usage estimate shows the literal is *still referenced from active code* (bucket a) despite being dead on the provider side, don't just close it silently — flag it for rotation-hygiene review in `evidence` (a revoked secret still hardcoded in a live code path is a process smell worth surfacing even when it's not currently exploitable).
- **No liveness signal at all** — Step 3 had nothing, and Step 4 either wasn't offered (not on the allowlist) or the user declined — fall back entirely to the Step 2 usage estimate, and be conservative about it. A hardcoded secret sitting in active application code with no way to confirm it's dead should stay `technical_verdict: "KEEP OPEN"` with `exploitability_rating` set from the usage estimate (`MEDIUM` for bucket a, `LOW` for bucket c, `LOW`-to-`CLOSE`-worthy for bucket b depending on how clearly dead the code is) rather than being closed on a guess. `verification_method` should read plainly as `"static assessment only — not liveness-confirmed"` so this never gets misread downstream as a confirmed result.

In every case, `evidence` should carry the concrete trail: the file:line of the secret itself, the file:line(s) supporting the usage-estimate bucket, and — when applicable — the exact liveness signal or probe outcome and its source (Aikido-reported vs. user-approved probe).
