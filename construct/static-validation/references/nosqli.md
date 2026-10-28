# nosqli: NoSQL / operator injection

## Claim to verify
Attacker-controlled **structure** (objects with `$ne`, `$gt`, `$regex`, `$where`, or JavaScript
for `$where`/`$function`) reaches a NoSQL query and changes its meaning, e.g. bypassing a
password check or widening a filter.

## Refute if
- The value is coerced to a primitive before reaching the query (`String(x)`, `str(x)`,
  `parseInt`), or schema validation rejects non-string types (Joi/zod/Pydantic `str` fields,
  Mongoose schema casting when `strictQuery`/`sanitizeFilter` is on).
- The body parser cannot produce objects for this input (e.g. only `express.text()`; but note the
  default `qs` query parser *does* produce objects from `a[$ne]=1`).
- A sanitiser such as `express-mongo-sanitize` / `mongo-sanitize` is applied on this path.
- The query uses the value only in a position where operators are not interpreted
  (e.g. `_id` via `ObjectId(x)` which throws on objects).

## Framework protections to check
- Mongoose casts top-level query values to the schema type; it does **not** protect `$where`,
  `$expr`, aggregation pipelines, or fields typed `Mixed`.
- Mongoose 6+ `sanitizeFilter` option; `strictQuery`.
- DynamoDB / Firestore SDKs take typed values; injection is rare unless expression strings are
  concatenated (`FilterExpression: "a = " + x`).

## confirmed_static when
A whole request object or field (that may be an object) is placed into a filter or update
document and no coercion/sanitiser is on the path; or input is concatenated into `$where` /
expression strings.

## Common false positives
- `findById(req.params.id)`: path params are always strings.
- Values validated by a schema that requires a string.

## Severity
Authentication bypass or cross-user data read: `high`/`critical`. Filter widening on own data:
`low`.

## Remediation
Coerce to primitives, validate types with a schema, never pass request objects as filters.
