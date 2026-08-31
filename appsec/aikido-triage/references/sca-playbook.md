# SCA Playbook

Lazy-loaded reference for Phase 3 of `/aikido-triage` — covers the SCA category (`issue_type` values `open_source`, `license`, `eol`). Populate the finding record defined in SKILL.md for every finding below.

---

## `open_source` findings

### Step 1 — extract package, installed version, and CVE/advisory ID

Primary source is `issue_title` and `issue_remediation` text. Recognize patterns like:

- `CVE-YYYY-NNNNN` — e.g. `CVE-2024-3568`
- `GHSA-xxxx-xxxx-xxxx` — GitHub Security Advisory format
- `<package>@<version> - <vuln name>` — e.g. `"lodash 4.17.15 - Prototype Pollution"`, where the version sits right next to the package name in plain text

Some issues additionally surface explicit package/version fields directly on the Aikido finding — treat these as available-when-relevant, not guaranteed. Use them when present; fall back to parsing title/remediation text when they aren't.

If no CVE/advisory ID can be extracted from the title or remediation text, fetch `issue_link` (WebFetch) to recover it before giving up — Aikido's issue detail page states it even when the list-view text is truncated.

### Step 2 — quick grep pre-check

Before deciding whether to chain out, search the app source for imports of the package (adapt to the language's import syntax — `import`/`require`/`from ... import`/`use`, etc.), and for the specific vulnerable function name if the title names one. This table is carried over from the prior version of this skill and is still correct:

| Scenario | Verdict |
|---|---|
| Package not imported anywhere in app source (transitive/build-only) | **CLOSE — Not Exploitable** |
| Package imported but vulnerable function never called | **CLOSE — Not Exploitable** |
| Package imported, vulnerable function called, no user input reaches it | **CLOSE — Not Exploitable** |
| Package imported, vulnerable function called with user-controlled input, no sanitization | **KEEP OPEN** |
| devDependency only (webpack-dev-server, jest, babel plugins) | **CLOSE — Not Exploitable** |

This table only settles the clean cases — a genuinely unused package or a pure dev-tool. Anything else moves to Step 3.

### Step 3 — mandatory chain to `/analyze-cve`

For anything not cleanly resolved by the quick grep — the package IS imported and there's a plausible reachable path, or you're unsure — invoke:

```
/analyze-cve <package> <installed_version> <cve-or-advisory-link>
```

This is declared **MANDATORY** in SKILL.md's chain commitments. Do not render a final verdict for the finding until `/analyze-cve` returns its report — a grep hit is not a completed source-to-sink trace. Do not skip this to save time on a case that "looks probably fine"; `/analyze-cve`'s own hard gate ("not imported → stop, not exploitable") is the authority here, not your own read of the grep results.

`/analyze-cve` trusts caller-supplied package/version/CVE info by design — do not re-verify those yourself before invoking it, that verification (if any) is its own optional internal step, not a precondition you owe it.

### Step 4 — map analyze-cve's output back into the finding record

`/analyze-cve` produces `CVE-YYYY-XXXXX-analysis.md` with an `## Exploitability Assessment` verdict and a mandatory trailing `## Tracking Tool Summary` line in the format `[Explanation]. Found in: file.ext:line, file.ext:line`. Map:

| analyze-cve output | Finding record field |
|---|---|
| Exploitability verdict — `HIGH` / `MEDIUM` / `LOW` / `NOT EXPLOITABLE`, verbatim | `exploitability_rating` |
| `NOT EXPLOITABLE` → `CLOSE`; `HIGH`/`MEDIUM` → `KEEP OPEN`; `LOW` → judgment call, see below | `technical_verdict` |
| Only set when `technical_verdict` is `CLOSE`: `"Not Exploitable"` | `close_category` |
| `"/analyze-cve dataflow trace"` | `verification_method` |
| The Tracking Tool Summary line, plus the report path (e.g. `Report: CVE-2024-3568-analysis.md`) | `evidence` |

`LOW` is the one case needing judgment: if the report's reasoning shows a real-but-hard-to-reach path (already-authenticated admin, a config flag that's off by default in this deployment), `CLOSE` with `close_category: "Not Exploitable"` and note the caveat in `evidence`. If the constraint is fragile or environment-dependent, `KEEP OPEN` instead and let Phase 4's business-impact scoring rank it — don't close on a marginal call.

---

## `license` findings

No CVE involved, and no chain to `/analyze-cve` — this is a native, lightweight check.

1. Read the flagged manifest (`package.json`, `Gemfile.lock`, a vendored `LICENSE` file, `requirements.txt` plus the package's own license metadata, etc.) at `file:line` to confirm the actual declared license.
2. Apply judgment:
   - **Permissive** (MIT, Apache-2.0, BSD-2/3-Clause, ISC) → `CLOSE`, `close_category: "Not Exploitable"`. Flag the distinction explicitly in `evidence` — this is a security-relevance call, not a legal clearance: e.g. *"MIT, permissive — closing as no security concern; license-terms compliance is a separate legal review, not covered by this closure."*
   - **Copyleft or otherwise incompatible with commercial use** (GPL, AGPL, SSPL, or anything the org's license policy flags) on a directly-shipped dependency → `KEEP OPEN`. Note in `evidence` that this is a compliance concern, not a vulnerability.
3. If no license policy is known for the org, default to `KEEP OPEN` so the finding stays visible for a human compliance decision — don't silently close something you have no policy basis to clear.

---

## `eol` findings

Native check, carried over from the prior version of this skill — no chain-out.

1. Read the actual version-pinning file (`.ruby-version`, `.nvmrc`, `package.json` `engines`, a `Dockerfile` base image tag, `go.mod`, etc.) to confirm the real installed/pinned version — don't trust Aikido's cached version blindly.
2. Look up the EOL date for that version (public EOL trackers, e.g. endoflife.date, or the vendor's own lifecycle page).
3. If EOL has passed: `KEEP OPEN`, and treat it as a `"Real Finding"`-style conclusion — document the EOL date and the recommended upgrade path/target version in `evidence`.
4. If EOL has not yet passed (Aikido flagged "approaching EOL" rather than past it), use judgment: `CLOSE` with the remaining runway noted if it's many months out and not urgent, or `KEEP OPEN` if it's imminent — state the actual date either way.

---

## Closing notes on the finding record

- `close_category` for this category: `"Not Exploitable"` for closed `open_source` and `license` findings; use `"Real Finding"` framing in the writeup for kept-open `eol` findings (EOL is a factual lifecycle condition, not a reachability judgment — `close_category` itself only applies to `CLOSE` verdicts, so it stays unset when `eol` findings are kept open).
- `exploitability_rating` is a code-reachability concept and only has real teeth for `open_source` findings. `license` and `eol` findings have no HIGH/MEDIUM/LOW concept:
  - When closed, set `exploitability_rating: "NOT EXPLOITABLE"`.
  - When kept open, set it to `"N/A"` and say so in `verification_method`/`evidence` — e.g. *"policy finding, not a code-reachability finding"* — so it isn't misread downstream as an exploitability HIGH just because the field was left blank.
