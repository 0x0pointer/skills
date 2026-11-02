# idor: Missing object-level authorization (IDOR / BOLA, cross-tenant)

## Claim to verify
An authenticated user can read or change an object belonging to another user or tenant by
supplying its identifier, because the object is loaded or modified without an ownership or
tenancy constraint.

## Refute if
- The load is scoped: the query includes the owner/tenant (`filter(id=..., user=request.user)`,
  `findByIdAndOwnerId`, `current_user.orders.get(id)`), or the object is fetched through the
  user's relation.
- An explicit check follows the load **before any effect or response** (`if obj.owner_id !=
  user.id: 404/403`), or a policy/voter/authorization service is called with the object.
- A framework mechanism enforces it on this path: DRF `get_object()` with
  `has_object_permission`, Laravel policies via `authorize()` / `can` middleware, Spring
  `@PreAuthorize` / `@PostAuthorize` with an ownership expression, ASP.NET resource-based
  `AuthorizeAsync`, ORM global tenant scopes / Hibernate filters / EF global query filters,
  Postgres row-level security keyed on the session user.
- The object is intentionally public (product intent visible in code or PR text: public
  profiles, published posts).
- The identifier is an unguessable capability *by design* (signed URL, random share token with
  >= 128 bits). Sequential or UUIDv1 ids are guessable; UUIDv4 alone is not authorization but
  lowers likelihood (keep `plausible`, lower severity).

## Framework protections to check
- DRF object permissions do **not** run for list views or when the view overrides `get()` and
  queries directly.
- Global tenant scopes are bypassed by raw SQL, `unscoped()`, `IgnoreQueryFilters()`,
  `withoutGlobalScopes()`, or a different manager.
- Tenant id taken from the request (header, body) rather than the principal is no protection.
- Nested resources: checking the parent (`/projects/{p}/tasks/{t}`) but loading the child by
  `t` alone lets `t` belong to another project.

## confirmed_static when
The handler is reachable by any authenticated user (or any member of a tenant), the cited load
or update uses the attacker-supplied id with no owner/tenant constraint, and no check or policy
runs between the load and the effect. Contrast with a sibling handler that does scope is strong
supporting evidence.

## Common false positives
- Admin-only endpoints where admins are expected to access everything (check the role guard).
- Lookups that are unscoped but followed by a check a few lines later or in a called service.

## Severity
Write/delete on others' objects or cross-tenant read of sensitive data: `high`; cross-tenant
on a multi-tenant SaaS: `critical`. Read of low-sensitivity data: `medium`.

## Remediation
Scope the query by the authenticated principal (owner or tenant) or call the policy check with
the loaded object before acting.
