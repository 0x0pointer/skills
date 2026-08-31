# Misconfiguration Playbook

Lazy-loaded reference for Phase 3 of `/aikido-triage` — covers the Misconfiguration category
(`issue_type` values `cloud`, `iac`, `docker_container`, `cloud_instance`, `scm_security`,
`surface_monitoring`). Populate the finding record defined in SKILL.md for every finding below.

None of these findings point at a line of application source code the way SAST does — they point
at a *declared configuration* or an *externally observed exposure*. The verification method is
therefore blast-radius reasoning against the actual config, not a taint trace. Every verdict in
this category defaults to **static-only** unless Step 4's live-chain gate is explicitly satisfied —
never let a well-reasoned static verdict read as if a live target confirmed it.

---

## Step 1 — Read the finding and the local source of truth

Start with Aikido's own detail: `issue_title`, `issue_remediation`, resource type, and whatever
identifiers Aikido attaches (bucket/role/ARN name, file/line, repo/workflow name, hostname/port for
`surface_monitoring`). Treat this as a pointer, not evidence — Aikido's remediation text is a
generic description of the rule that fired, not a description of *this* resource's actual blast
radius.

If the misconfigured resource is defined locally, read that definition before doing anything else.
The declared config is stronger evidence than Aikido's summary text every time:

- **`iac`** — the Terraform (`.tf`/`.tf.json`), CloudFormation (`.yaml`/`.json` template), Pulumi,
  or CDK source that declares the resource. Read the actual resource block, not just the resource
  type name.
- **`cloud`, `cloud_instance`** — often there is no IaC (the resource may have been created via
  console or a one-off script). If `issue_file`/`location` points at IaC, read it the same way as
  above; if not, you are reasoning from Aikido's live-scanned resource metadata alone — say so.
- **`docker_container`** — the `Dockerfile` and, if present, `docker-compose.yml`/`compose.yaml`
  or the Kubernetes manifest that runs the image. Base image, exposed ports, `USER` directive,
  capability grants (`--privileged`, `cap_add`), and mounted volumes all matter.
- **`scm_security`** — the GitHub Actions workflow (`.github/workflows/*.yml`) or equivalent CI
  config (GitLab CI, CircleCI) that Aikido flagged. Read the actual `permissions:` block, trigger
  conditions (`on: pull_request_target`, `workflow_run`), and any `id-token: write` / OIDC trust
  configuration.
- **`surface_monitoring`** — this category is inherently externally-observed (an open port, an
  exposed admin panel, a certificate on a live host) rather than something declared in a repo file.
  There is usually no local file to read; instead, grep the codebase for anything that provisions
  or documents that exposed asset (a deployment script, a load balancer config, a README noting the
  service is intentionally public) so you have *some* first-party context before reasoning about it
  in Step 2.

If no local definition exists anywhere in `CODEBASE_PATH` for a resource that should have one (an
`iac` finding with no matching Terraform file, for instance), note that explicitly in `evidence` —
it's itself a signal that the resource may be unmanaged, orphaned, or defined in a repo you don't
have access to, which feeds directly into Step 3's reachability judgment.

---

## Step 2 — Static blast-radius reasoning

This is the core of the playbook. The question is never "does this violate a best practice" — it's
"if this exact setting is exploited, what specifically does an attacker get." Reason from the
actual declared config you read in Step 1, and be concrete enough that the answer could be quoted
back to an engineer who will ask "okay, but what does that actually let someone do."

Work through these in order:

1. **What does the resource actually contain or grant?** Don't stop at the misconfiguration's
   name — trace what's on the other side of it.
   - A public S3 bucket / GCS bucket / Azure blob container: don't just note "publicly readable."
     Grep the application code and IaC for what actually gets written there — is this a static
     assets bucket serving a public website (low blast radius, arguably not even a real finding),
     or does application code write user uploads, exports, backups, logs, or database dumps to it
     (high blast radius — say specifically what kind of data based on what you can see written to
     it)?
   - An overly permissive IAM role or policy: read the actual policy document (the JSON/HCL, not
     Aikido's paraphrase). List the specific actions granted (`s3:*`, `iam:PassRole`,
     `sts:AssumeRole` on `*`, `ec2:*`) and the resource scope (`Resource: "*"` vs. a scoped ARN).
     `iam:PassRole` combined with a compute-creation permission is a privilege-escalation primitive
     — call that out by name if you see it, don't just say "too broad."
   - A missing or overly permissive network policy / security group / firewall rule: determine
     what is actually reachable as a result. A security group allowing `0.0.0.0/0` on port 22 is a
     different finding from one allowing `0.0.0.0/0` on a port that's already meant to be public
     (443 on a public load balancer). Read the target's own listener/service config to know which
     case you're in.
   - A Kubernetes RBAC binding, pod security context, or missing NetworkPolicy: what does the
     over-privileged ServiceAccount/role actually let a compromised pod do (read secrets
     cluster-wide? create pods? escape to the node via `hostPath`/`privileged: true`?). What's
     reachable from the pod's network namespace if no NetworkPolicy restricts egress/ingress?
   - A `docker_container` finding (running as root, `--privileged`, no resource limits, a
     vulnerable/EOL base image with a shell and network tools left in): what does that specific
     grant enable inside a container-escape or supply-chain scenario, not just "insecure Dockerfile
     practice" in the abstract.
   - An `scm_security` OIDC/trust-policy finding: read the actual trust policy condition. A trust
     policy scoped to `token.actions.githubusercontent.com:sub` with no `repo:` or `ref:` qualifier
     (or a wildcard like `repo:org/*:*`) means *any* workflow in *any* repo under that org/pattern
     can assume the role — state the actual condition you found and what it does or doesn't
     constrain.
   - A `surface_monitoring` exposure: identify what's actually running on the exposed
     port/endpoint (an admin panel, a database, a debug/metrics endpoint, an API) and what an
     unauthenticated caller could do with it, based on whatever first-party context you found in
     Step 1.

2. **Internet-facing or internal-only?** State this explicitly for every finding — it's the single
   biggest multiplier on blast radius. A resource reachable only from a private VPC/VNet with no
   public IP, no public load balancer target, and no internet gateway route is a materially
   different risk from the same misconfiguration on something with a public IP or public DNS name.
   Determine this from the IaC (subnet association, `associate_public_ip_address`, security group
   source ranges, whether a load balancer/ingress in front of it is internet-facing) rather than
   assuming from the resource type alone.

3. **Compensating controls in the same config.** Before finalizing the blast-radius read, check
   whether something else in the *same* declaration narrows it — these change the verdict and must
   be called out explicitly when present:
   - A bucket's ACL/public-access-block setting looks public, but a bucket *policy* on the same
     resource restricts access by source IP, VPC endpoint, or requires a signed URL / specific
     principal.
   - A broad IAM policy is attached, but a permissions boundary or SCP on the same account/OU caps
     what it can actually do in practice.
   - A security group allows a wide port range, but a NACL, WAF, or an authentication layer in
     front of the service (visible in the app code or another config file) still gates access.
   - A container runs as root, but a read-only root filesystem, dropped capabilities, or a
     seccomp/AppArmor profile meaningfully narrows what root-in-container can actually do.
   - Note the absence of compensating controls too, explicitly — "no bucket policy present to
     restrict the public ACL" is itself evidence, not a gap in your writeup.

Write the conclusion of this step as a specific sentence in `evidence`, e.g. *"S3 bucket
`app-user-exports` (defined in `infra/s3.tf:42`) has `block_public_acls = false` and no bucket
policy; application code in `export_service.py:88` writes signed customer data exports here —
public read of PII-bearing exports if exploited. No compensating IP/VPC restriction present."* —
not *"S3 bucket is public, which is a security best practice violation."*

---

## Step 3 — Deployed/reachability gate

Blast-radius reasoning tells you what *would* happen if the misconfiguration were live and in use.
This step asks whether it actually is. A resource that is not plausibly deployed is not
exploitable regardless of how bad the config looks in isolation, and that is grounds to close it
outright.

Check for the following signals of dead weight, in the local repo:

- The defining file lives under a path that signals non-production intent: `examples/`, `test/`,
  `fixtures/`, `archived/`, `deprecated/`, `sandbox/`, a personal scratch directory, or similar.
- It's a Terraform/CloudFormation **module** that is defined but never referenced by any root
  module, workspace, or stack that actually gets applied — grep the rest of the IaC tree for a
  `module "..." { source = "..." }` call (or stack include) that pulls it in. A module sitting
  unreferenced in the repo is not a deployed resource.
- It's a Kubernetes manifest or Helm values file for an environment that shows clear signs of
  decommissioning — referenced nowhere in current CI/CD deploy pipelines, superseded by a newer
  manifest for the same service, or accompanied by comments/commit history indicating the
  environment was torn down.
- A Dockerfile that is not the one actually built and shipped — check `docker-compose.yml`, CI
  build workflows, or a build script for which Dockerfile path is actually invoked; a leftover or
  alternate Dockerfile nothing builds from is not running anywhere.
- An `scm_security` workflow file with a trigger condition that structurally can't fire in this
  repo's actual usage (e.g. a workflow gated on a branch or environment that no longer exists).

If you find one or more of these signals and nothing in the repo contradicts them (no active
reference, no recent commit touching the "dead" path, no CI pipeline invoking it), render:

```
technical_verdict:  CLOSE
close_category:     Not Exploitable
```

and state the specific evidence for why you believe it's unused in the `evidence` field — name the
path, name what you grepped for and didn't find, don't just assert "looks unused."

If the resource is plausibly live — it's referenced by an applied root module, it's the Dockerfile
CI actually builds, it's a workflow that runs on every PR, or you simply can't find evidence either
way and the resource type is the kind that's normally always-on (e.g. most `cloud`/`cloud_instance`
findings, which by definition come from Aikido's live cloud scan and are near-certainly real,
running resources) — proceed to Step 4 with the blast-radius conclusion from Step 2 intact.

---

## Step 4 — Optional live chain (authorized access only)

If Steps 1–3 leave a real, plausibly-live, non-trivial-blast-radius misconfiguration, the next
question is whether it can be *live-confirmed* rather than left as a static judgment call. This
step only runs under one condition: **the user has already told you, earlier in this conversation,
that they have live target access authorized for this specific resource** — cloud credentials for
the account/subscription/project in question, cluster access for the K8s cluster in question, or a
reachable running instance of the exposed app/endpoint in question.

Do not ask "do you want me to test this live" as a generic offer, and do not invoke a live-testing
specialist skill speculatively "just to check." Authorization has to already be established for
*this* resource, not implied by the fact that a live-testing skill exists in the repo. If it isn't
established, skip straight to Step 5 and finalize as static-only.

When authorization does exist, route by resource type using this table:

| Resource type | Chain to | Notes |
|---|---|---|
| `cloud`, `cloud_instance` | `/cloud-security` | General cloud posture (AWS/Azure/GCP) — use for IAM, storage, serverless, and database exposure confirmation. |
| `docker_container`, or `iac` findings that are Kubernetes manifests | `/container-k8s-security` | Container/K8s-specific — use for RBAC, pod security, and container-escape confirmation. |
| `surface_monitoring` (exposed asset) | `/api-security` (if the exposed asset is an API) or `/ssl-tls-audit` (if it's a TLS/cert misconfiguration on an exposed endpoint) | Pick based on what Step 1/2 determined is actually exposed — don't default to one without checking. |
| `scm_security` — general | *(no strong existing specialist in this repo — stays static-only)* | Be honest that there's no perfect match here; don't force a chain into a skill that doesn't fit just to have something to invoke. |
| `scm_security` — specifically a CI/CD OIDC trust misconfiguration (e.g. an IAM role trust policy over-broadly trusting `token.actions.githubusercontent.com`) | `/cloud-identity-federation` | Only this specific sub-case has a good match — a generic branch-protection or secret-scanning `scm_security` finding does not chain here. |

Invoke the matched skill with the specific resource identifier and the blast-radius hypothesis from
Step 2 as context (what you expect to be exploitable and why), so the specialist skill's live
testing is targeted rather than a blind re-scan. Take its result — confirmed exploitable,
confirmed not exploitable, or inconclusive — and fold it directly into the verdict in Step 5.

If the resource type has no good specialist match (the `scm_security` general case), or the user
has not authorized live access, do not chain. Finalize as static-only per Step 5 below — this is a
normal, expected outcome for most findings in this category, not a shortcoming to apologize for.

---

## Step 5 — Verdict

Set the finding record fields from whichever step actually settled the case:

- **Settled at Step 3 (not deployed):** `technical_verdict: CLOSE`,
  `close_category: "Not Exploitable"`, `exploitability_rating: "NOT EXPLOITABLE"`,
  `verification_method: "static assessment only — not live-confirmed"`, and `evidence` naming the
  unused-path signal found.
- **Settled at Step 2 with strong compensating controls** (the misconfiguration is real but a
  bucket policy / permissions boundary / auth layer in the same config genuinely neutralizes it):
  `technical_verdict: CLOSE`, `close_category: "Not Exploitable"`,
  `exploitability_rating: "LOW"` or `"NOT EXPLOITABLE"` depending on how airtight the compensating
  control is, `verification_method: "static assessment only — not live-confirmed"`, `evidence`
  naming both the misconfiguration and the specific control that neutralizes it.
- **Real, live, high-blast-radius, no authorized live access (the common case):**
  `technical_verdict: KEEP OPEN`, `close_category` unset,
  `exploitability_rating` set from the Step 2 blast-radius severity (`HIGH` for a plausible direct
  compromise/data-exposure path, `MEDIUM` for a real but multi-step or partially-constrained path,
  `LOW` for a real gap with limited practical impact),
  `verification_method: "static assessment only — not live-confirmed"`, `evidence` carrying the
  Step 2 conclusion verbatim.
- **Live-chained at Step 4 and the specialist skill confirmed exploitability:**
  `technical_verdict: KEEP OPEN`, `exploitability_rating: "HIGH"` (or whatever the specialist skill
  itself concluded), `verification_method: "live-confirmed via /cloud-security"` (substitute the
  actual skill invoked), `evidence` citing the specialist skill's specific confirmation (the request
  that succeeded, the object retrieved, the role actually assumed).
- **Live-chained at Step 4 and the specialist skill found it NOT exploitable** (compensating
  control held up under live testing, resource wasn't actually reachable as feared):
  `technical_verdict: CLOSE`, `close_category: "Not Exploitable"`,
  `exploitability_rating: "NOT EXPLOITABLE"`,
  `verification_method: "live-confirmed via /cloud-security"` (substitute the actual skill),
  `evidence` citing what the live test actually showed.

The wording of `verification_method` is not cosmetic — Phase 4's business-impact scoring and Phase
7's final summary both surface it directly to the user. Never write `verification_method` in a way
that could be misread as live confirmation when only static reasoning was done, and never bury a
"static only" caveat inside `evidence` instead of stating it plainly in `verification_method` where
the downstream phases actually look for it.

---

## Closing rule

Live-chaining is the exception, not the default path, for this category. Run Steps 1–3 (read the
config, reason about blast radius, check whether it's actually deployed) on every single
misconfiguration finding regardless of how the rest of this playbook plays out. Only proceed to
Step 4 when the user has *already* established, earlier in the conversation, that live target
access is authorized for that specific resource — never invoke a live-testing specialist skill on
spec, and never let the mere existence of a matching skill in the routing table stand in for that
authorization. Absent it, the honest and complete answer is a static verdict labeled exactly as
that: `"static assessment only — not live-confirmed"`.
