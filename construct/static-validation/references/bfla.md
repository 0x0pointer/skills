# bfla: Missing function-level authorization

## Claim to verify
A user without the required role or permission can invoke a privileged function (admin action,
approval, export, impersonation, role change, configuration) because the handler lacks a role /
permission check, or the check is bypassable or fails open.

## Refute if
- A role/permission guard applies to this handler: decorator (`@permission_required`,
  `@PreAuthorize("hasRole('ADMIN')")`, `[Authorize(Roles = ...)]`, `@UseGuards(RolesGuard)` with
  `@Roles`), route-group middleware (`can:` / `role:` middleware, router-level dependency), or a
  security config rule matching this path (first-match order checked).
- The check is in the service method the handler calls, before any effect.
- The function is not privileged in this product (verify against PR intent and sibling
  handlers).

## Framework protections to check
- Global "authenticated" rules do not imply role checks.
- Method security annotations need enabling (`@EnableMethodSecurity`) and proxied invocation.
- Route patterns: a new path outside the protected prefix (`/admin/**` vs `/api/admin-tools`).
- Role taken from client-controlled data: request body, unverified JWT claims
  (`jwt.decode` without verification), cookies.
- Fail-open: exceptions in the check swallowed, `next()` in an error branch, entitlement or
  feature-flag lookups defaulting to allow, `if (user.role !== 'user')` treating unknown roles
  as privileged.
- UI-only hiding of buttons is not authorization.

## confirmed_static when
The handler is registered, reachable by a lower-privileged authenticated user, performs a cited
privileged effect, and no guard (decorator, middleware, config rule, service check) applies.

## Common false positives
- Handler mounted under a router whose middleware enforces the role (read the mount point).
- Checks performed in a base controller class or a shared dependency.

## Severity
Privilege escalation to admin or approval of money movement: `critical`/`high`. Low-impact
admin read: `medium`.

## Remediation
Add the role/permission guard used by sibling privileged handlers; fail closed on errors.
