# sqli: SQL injection

## Claim to verify
Attacker-controlled data becomes part of the **SQL text** (not a bound parameter) of a query
that is executed.

## Refute if (any one is enough)
- The value is passed as a bound parameter (`?`, `%s` with a params tuple, `$1`, `:name`,
  `#{}` in MyBatis, tagged-template `$queryRaw`, `FromSqlInterpolated`). Check that the driver
  call really receives a separate params argument: `cursor.execute("... %s" % x)` is **not**
  binding, `cursor.execute("... %s", (x,))` is.
- The value is coerced to a strictly typed value before use (`int()`, `UUID`, enum binding,
  `Number.isInteger`) and the coercion failure aborts the request.
- The interpolated part is an identifier chosen from a server-side allowlist (sort column map).
- The query is built only from constants, server config or values written by privileged code.
- The code path is not reachable (handler not registered, dead branch, test-only).

## Framework protections to check
- ORM query builders and finders (`filter(...)`, `where(col, val)`, Criteria, LINQ) bind values.
- Raw escapes are only partial: `.raw`, `.extra`, `text()`, `whereRaw`, `orderByRaw`,
  `knex.raw`, `$queryRawUnsafe`, `FromSqlRaw`, JPQL string concatenation, MyBatis `${}`.
- `LIKE` with a bound parameter is not SQLi (wildcard injection at most: `low`/`info`).
- Identifiers (`ORDER BY`, column, table names) cannot be bound; they need an allowlist.

## confirmed_static when
The route is registered and reachable by the stated attacker, the value flows from the request
to the SQL string through cited hops, and no binding, coercion or allowlist sits on the path.

## Common false positives
- Logging or error strings that contain SQL keywords.
- f-strings that only interpolate placeholders (`f"... WHERE id IN ({','.join('?' * n)})"`).
- Interpolating a server-generated table name or schema from config.
- Values typed as `int` by the framework before the handler runs (path converters `<int:id>`).

## Severity
Unauthenticated: `critical`. Any authenticated user: `high`. Admin-only: `medium`. Blind or
limited to `LIKE` wildcard abuse without boolean/time oracle: lower by one.

## Remediation
Use parameter binding; for identifiers, map user choices to a fixed allowlist.
