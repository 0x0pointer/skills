# Business Impact Rubric

Lazy-loaded reference for Phase 4 of `/aikido-triage`. Applies to every finding record produced in Phase 3, from every category (SCA/SAST/Secrets/Misconfiguration/Unmapped) — it is category-agnostic by design, since business impact depends on what the finding touches, not on which scanner produced it.

---

## What this rubric adds to the finding record

For every finding, add exactly two fields:

```
business_severity:      "Critical" | "High" | "Medium" | "Low"
business_justification: <required only when business_severity != aikido_severity — one line>
```

`business_severity` — not Aikido's raw `aikido_severity` — is what drives ranking in Phase 5 and Phase 7. It's computed by combining an **impact** assessment (what would actually be affected here) with the **likelihood** already established in Phase 3 (can an attacker actually reach it).

---

## Impact axis — read the finding's actual location, every time

Before assigning `business_severity` to any finding, look at what's actually at the flagged location. Don't infer from the finding's title or the filename alone — read the surrounding code, schema, or config the same way Phase 3 already did for the technical verdict. Walk through all four of these for every finding:

### 1. Data sensitivity at the finding's location

What does the affected file/service/resource actually touch?

- **PII** — names, addresses, emails, government IDs, contact details
- **Credentials/secrets** — API keys, tokens, passwords, signing keys
- **Financial/payment data** — cardholder data, bank details, transaction records
- **Health data** — anything HIPAA-relevant
- **None of the above** — internal metadata, UI copy, build artifacts, test fixtures

Look at the actual schema fields, the actual variable names holding the data, the actual request/response bodies passed through the flagged code — not the module name. A file called `utils.py` can format credit card receipts; a file called `payments.py` can contain nothing but a currency-formatting helper. Read before you classify.

### 2. System criticality

What role does the flagged service/component play?

- Authentication/authorization service
- Payment or checkout path
- Admin/internal tooling
- Core product functionality reachable by any authenticated user
- Public marketing site / docs / low-traffic internal batch job

The same technical finding does not carry the same weight everywhere. A reflected-input issue in the auth service is not equivalent to the identical pattern in a marketing microsite, even when Aikido assigns both the same raw severity — one sits on the path to account takeover, the other doesn't sit on a path to anything valuable.

### 3. Blast radius

If this were actually exploited, who is affected?

- A single tenant/customer's data
- All customers / the whole multi-tenant platform
- Internal-only, no customer-facing exposure

### 4. Compliance exposure

Would exploitation trigger a disclosure obligation — GDPR (PII), PCI-DSS (cardholder data), HIPAA (health data), SOC2 (control failure)? A finding that would force a breach notification carries impact beyond its immediate technical effect, even if the direct blast radius looks small.

Combine these four into a single impact rating — **Critical / High / Medium / Low** — using judgment: a finding that's severe on two or three axes (e.g. touches PII *and* sits on the auth path *and* affects all tenants) is Critical impact; a finding that's mild on all four (internal-only metadata, single low-traffic internal tool, no compliance angle) is Low impact.

---

## Likelihood axis — reuse Phase 3's exploitability_rating, don't re-derive it

Likelihood is not computed fresh at Phase 4. It's the category playbook's own `exploitability_rating` from the Phase 3 finding record — `HIGH` / `MEDIUM` / `LOW` / `NOT EXPLOITABLE` — carried forward as-is.

The playbooks in `sast-taint-playbook.md`, `sca-playbook.md`, `secrets-playbook.md`, and `misconfig-playbook.md` already did the actual reachability, taint, and liveness work to establish that rating. Re-deriving likelihood independently at Phase 4 would duplicate that work and risks contradicting it. Take the value as given.

---

## Combination matrix — Likelihood × Impact → business_severity

| Likelihood \ Impact | Critical | High | Medium | Low |
|---|---|---|---|---|
| **HIGH** | Critical | Critical | High | High |
| **MEDIUM** | High | High | Medium | Medium |
| **LOW** | Medium | Medium | Low | Low |
| **NOT EXPLOITABLE** | Low | Low | Low | Low |

Two asymmetries in this matrix are deliberate — call them out explicitly whenever they're the reason a finding's severity changed:

**`NOT EXPLOITABLE` always floors at Low, regardless of impact.** An unreachable finding doesn't matter how sensitive the data behind it is — if the code path is dead, provably unreachable, or the secret is confirmed inert, there is no attack surface left for the impact to act on. This is the main mechanism by which Phase 3's technical work (a taint trace proving a sink is unreachable, a liveness probe proving a key is dead) turns into a severity downgrade in Phase 4, even against an Aikido-raw Critical or High rating.

**`LOW` likelihood + `Critical` impact rounds up to Medium, never down to Low.** A low-probability path to a catastrophic outcome — a hard-to-reach, admin-only SQL injection that would expose the full customer PII table if it were ever reached — still deserves visibility. This mirrors the exact asymmetry the threat-modeling skill's own STRIDE table treats as canon: a "Low likelihood / Critical impact" threat still lands at High risk there, not Low. Don't let a technically-low exploitability rating fully erase a catastrophic-if-it-happens outcome.

Everything else in the matrix follows the intuitive diagonal: likelihood and impact reinforce each other, bounded by the two extremes above (`HIGH` + `Critical`/`High` → Critical at the top; `NOT EXPLOITABLE` → Low regardless of impact at the bottom).

---

## Justification rule

Whenever `business_severity` differs from the finding's raw `aikido_severity` — **in either direction**, upgrading or downgrading — `business_justification` is required. One line, specific, naming the actual asset/system/data involved. Never write a generic line like "reassessed based on business context" — name what was actually found and where.

**Upgrades** — the impact axis pushed the score above Aikido's raw rating:

- *"Aikido: Medium → Business Severity: Critical — hardcoded key found live in the primary payment-processing service touching cardholder data."*
- *"Aikido: Low → Business Severity: High — leaked credential is a valid, live admin API token for the production customer database; blast radius is the full multi-tenant platform."*

**Downgrades** — Phase 3's exploitability work established the finding matters less than Aikido's static rating suggests:

- *"Aikido: High → Business Severity: Low — flagged code path is unreachable (see exploitability_rating: NOT EXPLOITABLE); no live attack surface regardless of the pattern's severity in isolation."*
- *"Aikido: Critical → Business Severity: Medium — vulnerable function is called, but only from an internal batch job with no user-controlled input reaching it, and the affected table holds no PII or credentials."*

When `business_severity` matches `aikido_severity`, `business_justification` is not required — but see the guardrail below before treating a match as a shortcut.

---

## Guardrail against rubber-stamping

Never copy `aikido_severity` straight into `business_severity` without walking through the impact axis at least once, for every single finding. This applies even when the two end up matching — a match is only a legitimate outcome when the impact reasoning actually happened and landed there on its own merits; it is not a legitimate outcome when the reasoning was skipped because "Aikido already said High."

The failure mode to avoid: fifty findings triaged, `business_severity` copied verbatim from `aikido_severity` on every single one, zero justifications ever written. That output is indistinguishable from never having run Phase 4 at all, and it systematically misses both directions of misalignment it exists to catch — a Critical-labeled finding on a dead code path that should have been floored to Low, and a Medium-labeled hardcoded secret sitting live in the payment path that should have been raised to Critical. Do the four-axis read every time; let the matrix decide the number, not the scanner.
