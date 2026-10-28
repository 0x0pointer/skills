# mass-assignment: Object property authorization

## Claim to verify
A client can set a field it must not control (role, is_admin, status, price, balance, owner_id,
tenant_id, verified, plan) because the request body is bound wholesale to a persisted object.

## Refute if
- Binding uses an allowlist: explicit field list, `$fillable`, `fields = [...]` without the
  sensitive field, `read_only_fields`, a request DTO/schema without the field, `pick`/`only`,
  Nest `ValidationPipe({ whitelist: true })` with DTOs, `[Bind]`/`[BindNever]`, `@InitBinder`
  allowed fields.
- The sensitive field is overwritten from server state after binding and before save.
- The model has no sensitive fields (check the model/entity definition, including inherited
  and relation fields such as nested `user: { role }` writes).

## Framework protections to check
- Django `ModelForm` / DRF `ModelSerializer` with `fields = "__all__"` and no `read_only_fields`.
- Rails-style strong params permitting the key (value not validated).
- Laravel `$guarded = []`. Eloquent `forceFill`.
- Mongoose: schema fields not marked `immutable` / `select: false` are writable via
  `findByIdAndUpdate(id, req.body)`; `$set` operators in the body.
- Spring `@RequestBody Entity`, `BeanUtils.copyProperties`; .NET entity binding,
  `TryUpdateModelAsync` without include list.
- Pydantic: a single model used for both input and DB with `role` field having a default.

## confirmed_static when
The cited binding passes client data into a cited persisted object that has a cited sensitive
field, and no allowlist or overwrite exists on the path.

## Common false positives
- Sensitive field present but protected by DB trigger or service overwrite (read the save path).
- Admin-only endpoints where setting the field is intended.

## Severity
Role/admin/tenant/owner escalation: `critical`/`high`. Status/price/balance: `high` (often also
`workflow-bypass`/`value-tampering`; report under the class with the larger impact).
Cosmetic fields: no finding.

## Remediation
Bind to an input DTO with only writable fields, or use the framework's allowlist.
