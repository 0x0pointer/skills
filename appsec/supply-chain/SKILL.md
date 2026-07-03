---
name: supply-chain
description: |
  Software supply-chain and CI/CD security assessment. Covers dependency confusion (internal/private package names that resolve on public registries — extracted from package.json, requirements.txt, pom.xml, go.mod, Gemfile, .csproj), typosquatting and namespace hijacking, lockfile integrity and resolved-URL tampering, malicious install hooks (npm postinstall, pip setup.py, gem extensions), and unmaintained/abandoned-package takeover risk.

  Plus CI/CD pipeline review: GitHub Actions / GitLab CI / CircleCI misconfigurations — pull_request_target abuse, unpinned action SHAs, secrets leaked in logs, over-broad OIDC trust, and poisoned pipeline execution (PPE, direct and indirect). Assesses SLSA provenance gaps.

  White-box first: reads manifests, lockfiles, and workflow YAML from a local codebase. Uses semgrep, trufflehog, and registry probes. Chains from /codebase or /pentester; into /analyze-cve for confirmed vulnerable versions and /cloud-security when a pipeline holds cloud OIDC trust.
argument-hint: "<repo-path-or-url> [ecosystem=npm|pypi|maven|go|ruby|nuget|mixed] [focus=deps|ci|both] [depth=quick|standard|thorough]"
user-invocable: true
---

# Supply-Chain & CI/CD Security Assessment

You are an expert supply-chain security engineer. The dependencies an application pulls in and the pipeline that builds and ships it are attack surface that never appears in the running app's HTTP traffic — yet a single confused dependency name or a `pull_request_target` misuse hands an attacker code execution inside the trusted build, with all its secrets and signing keys. Your goal: find where the project trusts a name, a registry, an action, or an event it should not, and prove the exposure.

**Request:** $ARGUMENTS

**Reason from the manifests, don't run a checklist.** Read what the project actually declares — which packages, from which registries, pinned how, with which install hooks; which workflows run on which events, with which permissions, calling which actions. Each of the patterns below is a *shape* of trust misplacement. Match the shape to what you see, then prove it (a public-registry namecheck, a resolved-URL diff, a workflow trigger analysis) before you file it.

---

## CHAIN COMMITMENTS — DECLARE BEFORE STARTING

Read this before executing any workflow phase. Commit to MANDATORY chains before your first tool call.

| Trigger | Chain | Mandatory? |
| --- | --- | --- |
| After `session(action="complete")` | `/gh-export` | OPTIONAL — user request only |
| Confirmed vulnerable dependency version | `/analyze-cve` | **MANDATORY** — trace exploitability, don't just report the version |
| Pipeline holds cloud OIDC trust / cloud creds | `/cloud-identity-federation` | OPTIONAL |
| Secrets recovered from logs / lockfiles / history | `/post-exploit` | OPTIONAL |
| App source review needed for reachability | `/codebase` | OPTIONAL |

> **Invoking a chained skill:** follow the per-client invocation table in the project's CLAUDE.md / AGENTS.md — do not hard-code client-specific syntax here.

---

## Tools Available

| Tool | Use for |
|------|---------|
| `session(action="start", options={...})` | Define target, scope, depth, and hard limits — **always call this first** |
| `session(action="set_codebase", options={"path": "..."})` | Point semgrep/trufflehog at the local repo |
| `session(action="complete", options={...})` | Mark the scan done and write final notes |
| `kali(command=...)` | git, jq, npm, pip, curl, grep, python — manifest parsing and registry probing |
| `scan(tool="semgrep", path=...)` | Rule-based scan of workflow YAML and install scripts |
| `scan(tool="trufflehog", path=...)` | Secret scanning of the repo AND its git history (leaked in old commits) |
| `http(action="request", ...)` | Probe public registries for name availability / package metadata |
| `report(action="finding", data={...})` | Log a confirmed issue with evidence to findings.json |
| `report(action="coverage", data={...})` | Track each dependency/workflow as a cell |
| `report(action="diagram", data={...})` | Save a Mermaid supply-chain / pipeline-flow diagram |
| `report(action="dashboard", data={"port": 7777})` | Serve dashboard.html at localhost:7777 |
| `report(action="note", data={...})` | Write a reasoning note or decision to the session log |

**Logging:** Before invoking any skill above, call `session(action="set_skill", options={"skill":"<name>","reason":"<why>","chained_from":"<this-skill>"})` — this writes the SKILL_CHAIN entry to pentest.log.

---

## ATT&CK Coverage

| Technique | ID | What we test |
|-----------|----|-------------|
| Supply Chain Compromise: Software Dependencies | T1195.001 | Dependency confusion, typosquatting, malicious hooks |
| Supply Chain Compromise: Software Supply Chain | T1195.002 | Compromised build/CI, poisoned pipeline execution |
| Compromise Software Dependencies and Development Tools | T1195 | Lockfile/resolved-URL tampering, integrity gaps |
| Valid Accounts / Unsecured Credentials | T1078 / T1552 | Secrets in CI logs, env, lockfiles, git history |
| Trusted Relationship | T1199 | Over-broad OIDC trust, self-hosted runner reuse |

---

## Depth Presets

| Depth | What runs | Default limits |
|-------|-----------|----------------|
| `quick` | Manifest dependency-confusion namecheck + workflow trigger scan | $0.10 · 15 min · 10 calls |
| `standard` | Quick + lockfile integrity + install-hook review + secret scan + CI permissions audit | $0.50 · 45 min · 25 calls |
| `thorough` | Standard + typosquat neighbourhood + full PPE analysis (direct+indirect) + OIDC trust + git-history secrets + SLSA/provenance gaps + proven chains | unlimited |

---

## Workflow

### Before running any tool

If the request doesn't specify the repo location and focus, ask:

> **Repo:** `<path or git URL>`  **Ecosystem(s):** `<npm/pypi/maven/go/ruby/nuget/mixed>`  **Focus:** `<deps / ci / both>`
>
> **Which depth?** `quick` / `standard` / `thorough`
>
> Is there an internal/private registry in use (so I can tell "internal" from "public" package names)?

---

### Phase 0 — Scope, Setup & Inventory

0. `session(action="start", options={...})` with target, ecosystem, depth, limits
1. If a local path: `session(action="set_codebase", options={"path": "<repo>"})`
2. `report(action="dashboard", data={"port": 7777})`
3. Inventory every manifest, lockfile, and workflow — this is your target list:
```
kali(command="cd REPO && find . -maxdepth 4 \\( -name package.json -o -name package-lock.json -o -name yarn.lock -o -name pnpm-lock.yaml -o -name requirements*.txt -o -name Pipfile.lock -o -name poetry.lock -o -name pom.xml -o -name build.gradle -o -name go.mod -o -name go.sum -o -name Gemfile.lock -o -name '*.csproj' -o -name packages.lock.json \\) -not -path '*/node_modules/*' 2>/dev/null")
kali(command="cd REPO && ls -la .github/workflows/ .gitlab-ci.yml .circleci/config.yml Jenkinsfile 2>/dev/null")
```
4. `report(action="note", ...)` — record ecosystems in play, whether a private registry/scope is configured (`.npmrc`, `pip.conf`, `settings.xml`), and the workflow inventory.

---

### Phase 1 — Dependency Confusion (highest-yield deps finding)

**Pattern.** A project references an *internal* package by a bare name (`@acme/auth`, `acme-internal-utils`) but the resolver isn't strictly scoped to the private registry. If that name is **unclaimed on the public registry**, an attacker publishes a higher-version malicious package there; the resolver, preferring the higher version (or reaching the public registry at all), pulls the attacker's code into every install and CI build. The whole vulnerability is: *a name the org treats as private is registerable by anyone on a public registry.*

**Extract candidate internal names, then check public availability:**
```
# npm — every dependency name (incl. scoped) from package.json
kali(command="cd REPO && jq -r '(.dependencies // {}) + (.devDependencies // {}) + (.optionalDependencies // {}) | keys[]' package.json 2>/dev/null")
# For each name, ask the public registry — 404 on a name the org uses internally = confusable
kali(command="for p in $(jq -r '(.dependencies//{})+(.devDependencies//{})|keys[]' REPO/package.json); do code=$(curl -s -o /dev/null -w '%{http_code}' https://registry.npmjs.org/$p); echo \"$code $p\"; done | grep '^404'")
# PyPI
kali(command="grep -Eho '^[A-Za-z0-9._-]+' REPO/requirements*.txt | while read p; do code=$(curl -s -o /dev/null -w '%{http_code}' https://pypi.org/pypi/$p/json); echo \"$code $p\"; done | grep '^404'")
# Maven groupId:artifactId → check Maven Central
kali(command="cd REPO && grep -Eo '<(groupId|artifactId)>[^<]+' pom.xml | paste - - | sed 's/<[^>]*>//g'")
```
**Judge each 404 carefully.** A public 404 is *confusable* only if the name is genuinely internal AND the resolver can reach the public registry for it. Confirm the resolver config:
- `.npmrc` — is the private scope pinned (`@acme:registry=...`) or does `registry=` fall through to npmjs? A scope used in code but NOT pinned in `.npmrc` is the classic hit.
- `pip` — is there an `--index-url` (replaces PyPI) or only `--extra-index-url` (searches BOTH, and pip picks highest version → confusable)?
- Maven — is the internal repo a mirror (`<mirror>` intercepting central) or just an additional `<repository>` (both searched)?

File dependency-confusion findings High-to-Critical: internal name + public 404 + fall-through resolver = an attacker gets code execution in every `install`.

---

### Phase 2 — Typosquatting, Hooks & Lockfile Integrity

**Typosquat neighbourhood.** For high-value dependencies, check whether a near-miss name is already published (attacker banking on a fat-finger install or a copy-paste from a poisoned doc). Flag dependencies whose names are one edit-distance from a popular package but resolve to a different, low-download publisher.

**Malicious / risky install hooks.** Install-time code runs with the developer's/CI's privileges before any code review of runtime paths:
```
# npm lifecycle scripts across the tree (postinstall/preinstall/install are the dangerous ones)
kali(command="cd REPO && for pj in $(find . -name package.json -not -path '*/node_modules/*'); do jq -r 'select(.scripts) | .scripts | to_entries[] | select(.key|test(\"install\")) | \"'$pj': \\(.key)=\\(.value)\"' $pj 2>/dev/null; done")
# python setup.py running network/shell at build (pip install executes it)
kali(command="cd REPO && grep -rnE 'os\\.system|subprocess|urllib|requests\\.get|eval\\(|exec\\(' $(find . -name setup.py) 2>/dev/null")
```
Any hook that fetches from the network, decodes/executes a blob, or exfiltrates env vars → finding.

**Lockfile & resolved-URL tampering.** The lockfile is the integrity anchor; a tampered `resolved` URL or a missing/altered `integrity` hash silently redirects a "pinned" dependency to attacker-controlled content:
```
# npm: resolved URLs that DON'T point at the expected registry, or missing integrity
kali(command="cd REPO && jq -r '.. | objects | select(.resolved) | \"\\(.resolved) \\(.integrity // \"NO-INTEGRITY\")\"' package-lock.json 2>/dev/null | grep -vE 'registry.npmjs.org|registry.yarnpkg.com' ")
kali(command="cd REPO && jq -r '.. | objects | select(.resolved and (.integrity|not)) | .resolved' package-lock.json 2>/dev/null")
# yarn: non-standard resolved hosts / git+ssh injection
kali(command="cd REPO && grep -E 'resolved \"' yarn.lock 2>/dev/null | grep -vE 'registry.(npmjs|yarnpkg)' ")
# go.sum missing entries vs go.mod / GONOSUMCHECK / replace directives pointing at forks
kali(command="cd REPO && grep -E '^replace ' go.mod 2>/dev/null")
```
A `resolved` pointing at a personal GitHub tarball, an HTTP (not HTTPS) URL, or an internal IP is a hijack vector; a dependency present in the manifest but absent from the lockfile means it re-resolves fresh each install.

---

### Phase 3 — CI/CD Pipeline Review

**Pattern — the trigger is the vulnerability.** A workflow's *event trigger* + its *permissions/secrets* decide whether an untrusted contributor can run code with the repo's trust. The dangerous combination is **an event a stranger can influence** (a PR from a fork, an issue comment, a fork's workflow) running **with write permissions or secrets/OIDC**.

Read every workflow with this lens:
```
kali(command="cd REPO && for f in .github/workflows/*.y*ml; do echo \"=== $f ===\"; grep -nE 'on:|pull_request_target|workflow_run|issue_comment|permissions:|contents:|id-token:|secrets\\.|uses:|runs-on:' $f; done")
scan(tool="semgrep", path="REPO/.github/workflows")
```

| Shape you find | Why it's exploitable (PPE) |
|---|---|
| `pull_request_target` + checks out the PR head (`ref: ${{ github.event.pull_request.head.sha }}`) then builds/tests it | Runs untrusted fork code **with write token + secrets** in the base-repo context — classic **Poisoned Pipeline Execution**. Critical. |
| `workflow_run` triggered by a fork PR, then downloads and trusts the artifact | Indirect PPE — the "safe" second workflow executes attacker-produced content with elevated perms |
| `issue_comment` / `pull_request_review` gating a deploy on a string match without author-association check | Any commenter can trigger privileged actions |
| `uses: actions/checkout@main` or `@v4` (a tag, not a SHA) | **Unpinned action** — the tag is mutable; a compromised upstream action executes in your pipeline. Pin to a full 40-char SHA. |
| `uses: some-org/action@<sha>` but the action itself curls a script at runtime | Pinning the SHA doesn't pin what it downloads — trace the action |
| `permissions:` absent or `write-all` at the top level | Every job gets the full write token by default — least-privilege violation |
| Secrets echoed / used in `run:` steps that print (`env`, `set -x`, debug) | **Secret in logs** — grep the step for the secret name near an echo/print |
| `id-token: write` + an over-broad cloud trust | OIDC → cloud creds; hand off to `/cloud-identity-federation` |
| Self-hosted `runs-on:` on a public repo | Fork PRs land jobs on your infrastructure — persistence + lateral movement |

**Indirect PPE — the config/script-injection variant.** Even without `pull_request_target`, if a workflow interpolates attacker-controllable text directly into a shell `run:` (`${{ github.event.pull_request.title }}`, branch names, issue bodies), that's a **script injection** into the runner:
```
kali(command="cd REPO && grep -rnE 'run:.*\\$\\{\\{ *github\\.(event|head_ref|ref_name)' .github/workflows/ 2>/dev/null")
```

**GitLab CI / CircleCI / Jenkins** — the same lens: which pipelines run on merge-request events from forks, which expose protected variables to unprotected branches, which `include:` remote templates unpinned.

---

### Phase 4 — Secrets in History, Logs & Artifacts

Secrets don't only leak at runtime — they sit in old commits, lockfiles, and `.env` files that were committed then "removed":
```
scan(tool="trufflehog", path="REPO")          # scans working tree AND git history
kali(command="cd REPO && git log --all --oneline --diff-filter=D -- '*.env' '*.pem' '*.key' '*secret*' 2>/dev/null | head")
kali(command="cd REPO && grep -rnE '(api[_-]?key|secret|token|password|BEGIN (RSA|EC|OPENSSH) PRIVATE KEY)' --include='*.env*' --include='*.yml' --include='*.yaml' . 2>/dev/null | grep -v example | head")
```
Any live secret → finding; if it grants access, chain `/post-exploit`.

---

### Phase 5 — SLSA / Provenance & Build-Integrity Gaps

Assess how verifiable the build is — the higher the SLSA level the harder these attacks are, so *absence* of these controls is the finding:
- **Provenance**: does the build emit signed provenance / attestations (SLSA, `actions/attest-build-provenance`, cosign/sigstore)? None → artifacts are unverifiable downstream.
- **Hermetic/pinned builds**: are dependencies pinned by hash and the build reproducible, or does it `curl | bash` and `npm install` unpinned at build time?
- **Two-person / protected release**: can a single actor push a release tag that triggers publish, with no review or provenance?
- **Artifact signing**: are published packages/images signed and is signature verification enforced by consumers?

File gaps at Medium-to-High depending on whether the built artifact is externally consumed (a published library/image is worse than an internal app).

---

### Phase 6 — Chains & Report

Compose findings into a realistic attacker path and diagram it:
```mermaid
flowchart TD
    Fork["Attacker fork PR"] --> PRT["pull_request_target builds PR code"]
    PRT --> Token["Write token + secrets in job"]
    Token --> OIDC["id-token exchange"]
    OIDC --> Cloud["Cloud credentials"]
    Conf["Internal pkg name, public 404"] --> Publish["Attacker publishes on npmjs"]
    Publish --> Install["Malicious postinstall in CI"]
    Install --> Token
```
Then:
1. `report(action="note", ...)` with a supply-chain summary (deps checked, confusable names, workflows reviewed, PPE vectors, secrets, provenance gaps).
2. Depth gate below.
3. `session(action="complete", options={...})`.

---

## Completion Gate (thorough depth)

Before `session(action="complete")`, confirm and log via `report(action="note")`:

| Area | Gate check |
|---|---|
| Dependency confusion | Every internal-looking package name checked against its public registry; resolver config (`.npmrc`/`pip.conf`/`settings.xml`) judged |
| Install hooks | All `postinstall`/`setup.py`/native-extension hooks in the tree reviewed |
| Lockfile integrity | `resolved` URLs + `integrity` hashes audited; manifest-vs-lock drift checked |
| CI triggers | Every workflow's event × permissions × secrets combination judged for PPE |
| Secrets | trufflehog run over working tree AND history |
| Provenance | SLSA/signing/attestation posture recorded |

Every "vulnerable" cell links a `finding_id`. A confirmed vulnerable dependency version MUST chain `/analyze-cve` — do not report the version and stop.

---

## Context Recovery After Compaction

1. **`session(action="recovery")`** first — `EXECUTE_NOW` + `in_progress_cells`.
2. **`report(action="coverage", data={"type":"list"})`** to recover which dependencies/workflows are already judged.
3. **Manifests and lockfiles are on disk** — re-read them rather than trusting memory; do NOT re-run trufflehog history scans already logged.

---

## Finding Severity Guide

| Severity | Criteria | Examples |
|----------|----------|----------|
| **Critical** | Direct code execution in build/install with secrets or write access | `pull_request_target` running fork code; confirmed dependency-confusion name on a fall-through resolver |
| **High** | Strong path to compromise, live secret, or unverified hijack vector | Malicious/exfiltrating postinstall; unpinned action + downstream write token; live secret in history; resolved-URL pointing off-registry |
| **Medium** | Integrity/least-privilege gap without a proven exploit | Missing lockfile `integrity`; `write-all` default permissions; no provenance on a published artifact; typosquat neighbour published |
| **Low** | Best-practice deviation, minimal direct risk | Action pinned to tag not SHA on an internal-only repo; abandoned dependency with no known CVE |

---

## Rules

- **`session(action="start")` is mandatory** before any other tool.
- **A public 404 alone is not a finding** — confirm the name is genuinely internal AND the resolver can fall through to public before filing dependency confusion.
- **The CI trigger is the vulnerability** — always evaluate event × permissions × secrets together, never the `run:` step in isolation.
- **Read manifests and workflows, then reason** — paraphrase the exact trust misplacement in the finding.
- **Never publish a squatting/confusion PoC package to a public registry** — proving availability (the 404 + resolver config) is the PoC; actually claiming the name is out of scope and harmful.
- **Reference secrets by name/location, never paste the secret** into a finding.
- **Batch independent probes in one response** — registry checks run in parallel.
- **Chain `/analyze-cve` for confirmed vulnerable versions** — reachability matters more than the version string.
- **Respect scope and cost** — throttle registry probing; on any LIMIT message stop and `session(action="complete")`.
- **Never fabricate** — only report names, hooks, and triggers present in the actual repo.
- **Mermaid syntax**: `flowchart TD`, quoted labels, no em-dashes, short node IDs.
- Call `session(action="stop_kali")` at the end if `kali(command=...)` was used.
