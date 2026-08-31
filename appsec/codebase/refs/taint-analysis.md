# Taint Analysis Methodology

Lazy-loaded reference for Phase 5 Categories 1 (Injection), 3 (Deserialization), 5 (File Handling), and 7 (SSRF) of the `/codebase` skill. Run this 5-step sequence against every candidate finding in these categories — verify the sink, trace the taint, identify the true source, map every trust boundary crossed, then render a reachability verdict that rolls into severity. Each step is a separate, deliberate check — do not collapse sink-verification and taint-tracing into one "grep found it, looks bad" read, and do not skip the trust-boundary step because a control exists somewhere upstream in the architecture diagram — "somewhere in the architecture" is not evidence for a specific finding.

---

## Step 1 — Verify the sink is real

Read the flagged `file:line`, plus enough surrounding context (roughly 10 lines each side, more if the function is short) to see the call in its actual context. Confirm the dangerous pattern is present in **executable** code — not a comment, a string literal, a test fixture/mock, or dead/unreachable code.

Rule out, specifically:
- The match is inside a comment, docstring, or commented-out code.
- The match is inside a string literal — a log line or error message that mentions `exec(` or `SELECT` as text, not an actual call.
- The match is in a test file, fixture, or mock/stub — check whether the file lives under `test`/`spec`/`__tests__`/`fixtures` and whether it's excluded from the production build.
- The match is dead or unreachable code — a function never called anywhere, a branch behind a condition that can never be true, code behind a feature flag permanently off, or a file excluded from the build/deploy artifact.

If the sink isn't real, **stop here** — the finding is a false positive. No `trace[]` is needed; do not proceed to Step 2.

### Sink recognition per category

**Injection (ASVS V1.2):**
- Real: `cursor.execute(f"SELECT * FROM orders WHERE id = {order_id}")`, `db.raw("... " + input)`, `connection.exec(query_string)` — a string built with concatenation/interpolation and handed to a raw-execute call.
  Not real: `cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))`, `db.query(sql, params)` — parameterized/bound-variable calls that superficially resemble the dangerous shape but bind values out-of-band.
- Real: `subprocess.run(f"convert {filename} out.png", shell=True)`, `os.system(cmd)`, `child_process.exec(cmd)` — a shell string assembled from input.
  Not real: `logger.info(f"about to exec command: {cmd}")` — the word "exec" appearing in a log message, not a call to it. `subprocess.run(["convert", filename, "out.png"])` (argv list, no shell) closes off shell metacharacter injection even if `filename` is unsanitized — note this distinction in the trace rather than treating it as equivalent to the shell=True form.
- Real: `Template(user_input).render()`, `render_template_string(input)`, `eval(f"...{input}...")` in an SSTI-capable engine — template *source* built from input.
  Not real: `render_template("page.html", value=user_input)` — passing input as *data* to a safe templating call, not as template *code*.

**Deserialization (ASVS V1.5):**
- Real: `pickle.load(untrusted_bytes)` / `pickle.loads(request.body)`, `yaml.load(data)` with the default `Loader` (or explicit `Loader=yaml.Loader`/`UnsafeLoader`), Java `ObjectInputStream(untrusted_stream).readObject()`, PHP `unserialize($_POST['data'])`, Node `node-serialize` `unserialize()` — a call on bytes that originate outside the trust boundary.
  Not real: `yaml.safe_load(data)`, `yaml.load(data, Loader=yaml.SafeLoader)`, `json.loads(data)`, PHP `json_decode()` — safe equivalents that don't reconstruct arbitrary object graphs.
- Also check JSON libraries with polymorphic typing enabled (Jackson `@JsonTypeInfo`/`enableDefaultTyping()`, Newtonsoft `TypeNameHandling.All`/`.Auto`) — these behave like unsafe deserializers even though the wire format is JSON.

**File Handling (ASVS V5):**
- Real: `open(os.path.join(base_dir, request.args["filename"]))`, `File(userSuppliedName).getCanonicalPath()` used directly in a read/write/delete call, `send_file(f"/uploads/{filename}")` — a path where a user-controlled segment reaches a filesystem call without normalization/allowlisting against a base directory.
  Not real: `open("/etc/app/config.yaml")`, `open(STATIC_ASSET_PATH)` — a hardcoded path with no user-influenced segment.
- Check specifically whether path normalization/containment happens before the filesystem call (`os.path.realpath()` + a prefix check, `Path.resolve()` + `startswith`) — a `..`-strip via naive string replace is not equivalent to real containment (double-encoding, `....//`, symlinks can bypass a strip-based filter).

**SSRF (ASVS V*, new Category 7):**
- Real: `requests.get(user_supplied_url)`, `fetch(req.body.callbackUrl)`, `HttpClient.execute(new HttpGet(target))` where `target`/`callbackUrl`/the host component is user-influenced — an outbound HTTP/TCP call where the destination host, port, or full URL comes from external input (webhook registration URLs, "import from URL" features, PDF/image-fetch-from-URL, OAuth/OIDC dynamic client metadata like `jwks_uri`/`logo_uri`, avatar-by-URL uploads).
  Not real: `requests.get(INTERNAL_METRICS_ENDPOINT)`, a call to a fixed, hardcoded internal service URL with no request-derived component in the host/path — that's normal internal service-to-service traffic, not SSRF.
- If the URL is partially user-controlled (e.g. only a path suffix appended to a fixed host), the sink is real but the exploitable *scope* is narrower — carry that nuance into Step 2 rather than treating it as full arbitrary-destination SSRF.

This step alone resolves a meaningful share of candidate findings across all four categories — a pattern match tells you what *shape* of code triggered it, not that a vulnerability exists.

---

## Step 2 — Taint analysis: build the full source-to-sink propagation chain

This is a distinct activity from Step 1, not a continuation of it. Many findings die at Step 1 before a trace is ever needed — do not build a trace for a sink you haven't first confirmed is real, and do not treat "grep found the sink" as taint analysis in itself. This step is not complete until you have actually read every intermediate file; an inferred call chain ("this probably gets called from the handler") is not a trace.

Once the sink is confirmed real, walk **backward** from it. For every hop between the sink and wherever the value first enters the codebase, document:
- What calls this function (the caller, found by reading the caller — not assumed from the name).
- What the tainted value looks like at that point (raw string? partially transformed? wrapped in an object?).
- What — if anything — transforms, validates, or sanitizes it along the way, and whether that transformation actually neutralizes the payload shape relevant to this sink. A `.strip()` or a length cap does not neutralize SQL injection or SSRF; a parameterized rebind, an allowlist match against a fixed set of hosts, or a canonicalized-path prefix check usually does.

This produces the `entrypoint` → one-or-more `propagation` → `sink` sequence the skill's `trace[]` schema requires:

```
report(action="finding", data={
  "title": "SSRF via webhook callback URL",
  "severity": "high", "target": "/path/to/repo",
  "description": "...", "evidence": "...",
  "trace": [
    {"kind": "entrypoint",  "file": "api/webhooks.py",   "line": 51,  "scope": "register_webhook", "description": "callback_url taken from request body, unvalidated"},
    {"kind": "propagation", "file": "services/notify.py","line": 30,  "scope": "send_notification","description": "callback_url passed through unchanged to the HTTP client call"},
    {"kind": "sink",        "file": "services/notify.py","line": 33,  "scope": "send_notification","description": "requests.post(callback_url, ...) — outbound request to attacker-controlled host"}
  ]
})
```

Add as many `propagation` steps as there are real hops — don't compress a three-hop chain into one row because the middle hop "obviously" does nothing. If the trace terminates without ever reaching an external entry point (the value is fully constructed from constants and internal state at every hop you can find), that is itself the outcome of Step 3 below — don't force an `entrypoint` that isn't real.

---

## Step 3 — Identify the true source

Classify the origin the trace terminates at:

- **Externally controllable** — an HTTP request parameter, header, body field, cookie, a queue/message payload, a webhook payload, a third-party API response the app consumes, uploaded file content or metadata, anything an outside party can set directly or indirectly.
- **Internal/trusted only** — a hardcoded literal, a value read from a config file or environment variable the application controls, an admin-only CLI argument, a value only ever set by other trusted internal code with no path from any external input.

If internal/trusted only, and no path — direct or multi-hop — exists by which external input could reach it, **short-circuit here**: not exploitable, don't proceed to Step 4. State explicitly what you checked to rule out an external path (e.g. "grepped all callers of `build_filter()`; every call site passes a hardcoded internal constant, none derive from request data").

If externally controllable, continue to Step 4.

---

## Step 4 — Trust boundary / proxy crossing

**This is the step this skill's per-finding flow is currently missing entirely** — today a trust boundary only ever appears as a label on the Phase 1/Phase 7 architecture diagram, never as a per-finding check. A tainted value can be externally controllable and still never reach the sink in exploitable form, because it crosses one or more boundaries on the way that neutralize or gate it. Conversely, teams routinely *assume* a boundary control exists ("the gateway validates that") without the codebase actually proving it. This step exists to map the real boundaries and check each one specifically against this payload — not to note that boundaries exist somewhere in general.

For sources that survive Step 3, enumerate every boundary the tainted value actually crosses between source and sink. Concrete boundaries to look for, adapted to what this codebase actually has:
- Public internet → WAF/CDN → reverse proxy / API gateway → application service → internal service mesh → database.
- External webhook → signature-verification middleware → handler.
- Public endpoint → authentication middleware → authorization check → business logic → sink.
- Message-queue consumer → schema validation → handler.

For each boundary actually crossed, do two things:

1. **Name the specific control that exists there** — auth middleware, an input-validation gateway, a WAF rule, a network ACL, mTLS between services, a signature check, a schema validator — and point to the file/config that implements it (middleware registration, gateway config, WAF ruleset, ingress annotation).
2. **Reason about whether that control would neutralize *this specific* payload/pattern** — not just whether a control exists somewhere. An auth middleware that requires a valid session says nothing about whether the session-holder's input is then injectable. A WAF rule tuned for classic `' OR 1=1` may not catch a blind time-based SQLi payload. An SSRF allowlist that blocks `169.254.169.254` literally doesn't stop a DNS-rebinding or redirect-based bypass to the same address. Say explicitly which payload shape the control would or wouldn't stop.

If no evidence of a boundary or control exists in the codebase — no gateway config in the repo, no middleware file, nothing in IaC — **say so explicitly** rather than assuming production has one "probably." Record that as a static-assessment limitation and treat the path as unmitigated for Step 5.

**This is exactly where a `"boundary"` trace step belongs.** It uses the same shape as `entrypoint`/`propagation`/`sink` — real `file`/`line`/`scope`/`description`, resolved and rejected by the server the same way if hallucinated — inserted between the relevant `propagation` step and the `sink`:

```
{"kind": "boundary", "file": "middleware/auth.py", "line": 24, "scope": "require_session", "description": "requires a valid session cookie; does not validate or restrict the callback_url parameter"}
```

A `boundary` step is **expected** whenever the source is externally controllable and any boundary is actually crossed — omit it only when the flow never leaves a single trust zone (e.g. an internal batch job reading its own config, with no external-facing hop in between).

---

## Step 5 — Reachability verdict, rolled into severity

Classify reachability using what Steps 2-4 established:

- **Directly reachable** — no authentication required, and no boundary control found in Step 4 blocks or meaningfully hinders this specific payload.
- **Reachable-with-preconditions** — reaching the sink requires something beyond an anonymous request: a valid authenticated session, network-level access (VPN, internal-only network), a specific role/permission, or multi-step setup (e.g. must first create a resource you then attack).
- **Not reachable** — the code path is dead/unreachable (should have been caught at Step 1, reconfirm here if Step 2's trace revealed it), or a Step 4 control neutralizes this specific payload, or the path is unauthenticated-internal-only with no route from any external input.

Do not invent a separate rating scale — tie this directly to this skill's existing severity doctrine (`Severity = likelihood × impact`, from the Finding Severity Guide in `SKILL.md`):

| Step 5 outcome | Maps toward |
|---|---|
| Directly reachable | **Critical** or **High**, depending on impact (RCE/data breach/auth bypass → Critical; significant weakness needing moderate effort → High) |
| Reachable-with-preconditions | **High** or **Medium**, depending on impact and how restrictive the precondition is |
| Not reachable | Not a reportable finding — or a **Low** hardening note at most, per the existing "defense-in-depth gaps are LOW" rule. Never High/Critical when an existing control already stops the payload |

---

## Mapping outcomes to the `trace[]` schema

| Step | Outcome | `trace[]` contribution |
|---|---|---|
| 1 | Sink not real | No `trace[]` — not a finding |
| 2 | Sink real, chain built | First step: `kind:"entrypoint"`. One or more `kind:"propagation"` steps for each real hop |
| 3 | Source internal/trusted only, no external path | Stop — not exploitable, no finding filed |
| 3 | Source externally controllable | Continue; the `entrypoint` step's `description` should name the concrete external source |
| 4 | Boundary/control found and evaluated | Insert `kind:"boundary"` between the relevant `propagation` step and the `sink` |
| 4 | No boundary crossed (single trust zone) | Omit `boundary` — this is the only case where its absence is correct |
| 5 | Reachability verdict | Final step is always `kind:"sink"`; overall trace has ≥2 steps; severity set per the table above |

Confidence rating (already required by this skill's rules) follows trace completeness directly: `high` = full source-to-sink trace confirmed with real `file:line` through Steps 1-5; `medium` = partial trace, likely but not fully verified (e.g. Step 4 boundary evidence is incomplete); `low` = pattern-only, no complete trace (should be rare if Step 1 was applied honestly — a pattern-only finding that can't be traced usually means Step 1 wasn't actually finished).

This same 5-step methodology serves Phase 5 Categories 1 (Injection), 3 (Deserialization), 5 (File Handling), and 7 (SSRF) — only the sink-recognition specifics in Step 1 differ per category; Steps 2 through 5 are identical across all four.
