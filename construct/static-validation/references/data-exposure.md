# data-exposure: Excessive or sensitive data exposure

## Claim to verify
A response, log, export, error message or event exposes data the recipient must not see:
secrets (password hashes, tokens, API keys), other users' personal data, internal fields
(roles, flags, internal notes), or more rows than the caller owns.

## Refute if
- The response is built from an explicit schema/serializer/DTO that omits the field
  (`response_model`, DRF serializer `fields`, `@JsonIgnore`, `select: false`, `[JsonIgnore]`,
  `$hidden`), and that schema is what is actually returned on this path.
- The field is not sensitive for this recipient (own data, intended public profile fields).
- The endpoint is restricted to roles entitled to the data.

## Framework protections to check
- Returning ORM objects directly (`res.json(user)`, `return user.__dict__`, `model_dump()` of the
  DB model, default Jackson/System.Text.Json of entities) serialises every field, including
  future ones.
- `response_model` in FastAPI filters; returning a `dict` from a route with no `response_model`
  does not.
- Lazy-loaded relations serialised into responses (user -> organisation -> all members).
- Logging full request bodies, headers (`Authorization`), or tokens; exception handlers that
  return stack traces or SQL in production.
- List endpoints without owner/tenant filter (also `idor`; report under the class with the
  larger impact).

## confirmed_static when
The cited response or log construction includes a cited sensitive field or unfiltered row set,
on a path reachable by a recipient not entitled to it.

## Common false positives
- Debug output guarded by a setting that is off in production config in the repo.
- Hashes of non-secret values.

## Severity
Credentials/tokens/password hashes or bulk PII of other users: `high`. Single fields of other
users' PII: `medium`. Internal flags: `low`.

## Remediation
Return explicit response schemas with only the intended fields; redact secrets from logs.
