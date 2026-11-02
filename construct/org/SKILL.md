---
name: org
description: Company-specific security knowledge for reviewing this organisation's repositories - internal authentication and authorization libraries, known-safe wrappers that neutralise specific bug classes, tenancy model, and domain glossary. Consult before raising or refuting a hypothesis that depends on in-house code.
---

# Organisation knowledge

> **Status: template.** Sections marked `TODO(appsec)` must be filled in by AppSec before this
> skill carries weight. Until then, treat every in-house helper as unknown: read its source
> before relying on it, and do not assume it is safe or unsafe.

Use this skill to:

- recognise in-house auth and authorization helpers, so a check is not missed (false positive)
  or wrongly assumed (false negative);
- recognise **known-safe wrappers** whose use refutes a specific bug class;
- understand domain terms used in PR descriptions and code, so business-logic invariants are
  stated correctly.

The entries here are claims maintained by AppSec. They still need the usual evidence: when you
rely on an entry to refute a hypothesis, cite the call site of the wrapper in the reviewed code,
and say in `reasoning` (or `assumed_guards`) that you relied on the org skill entry by name.

## Reference files

- [Internal auth libraries](references/auth-libraries.md): how identity, roles and tenancy are
  established and checked.
- [Known-safe wrappers](references/safe-wrappers.md): helpers that neutralise a bug class, and
  the conditions under which they do.
- [Domain glossary](references/glossary.md): business terms, flows and their invariants.

## Tenancy model

`TODO(appsec)`: describe the default model. Example of the level of detail wanted:

- Every customer-facing record carries `tenant_id`; it is set from the authenticated principal by
  `TODO(appsec): <middleware or base class>`, never from the request.
- Repositories extend `TODO(appsec): <BaseRepository>` which applies the tenant filter
  automatically; raw SQL and `TODO(appsec): <escape hatch>` bypass it.
- Cross-tenant access is only legitimate in `TODO(appsec): <list of admin/support services>`.

## Risk priorities

`TODO(appsec)`: list the flows that matter most (e.g. payments, payouts, identity verification,
data export), so that hypotheses touching them are ranked first.

## How this affects outputs

- `assumed_guards` (hypothesise) and `guards[]` (static_verify) should name the in-house control
  as written here (e.g. "TenantScopedRepository applies tenant filter").
- A known-safe wrapper used correctly is grounds for `verdict: refuted`, with a citation of the
  wrapper call in the reviewed code.
- A known-safe wrapper used outside its stated conditions is not a guard.
- Run `prsec-cite check <your output file>` when a shell is available, as for any citation.
