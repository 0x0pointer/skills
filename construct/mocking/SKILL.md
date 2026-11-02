---
name: mocking
description: Provide what the PR's app needs around it in a dynamic environment - catalog mock services (postgres, mysql, redis, mongo, mailpit, oauth2) with their fixed connection strings, schema and seed data, test users, tenants and roles for authorization PoCs, stubs for third-party HTTP APIs, and how the sink records every call to an unknown host instead of letting it out. Used by the env and dynamic stages.
---

# Mocking services, users and third parties

The app under test runs on an internal network with no internet access. Everything it talks to
is either a **catalog service** you ask for in the EnvSpec, a **stub** you define, or the
**sink**, which answers everything else. This skill says what each provides and how to put the
data a PoC needs into it in a way an agent-free replay can repeat.

## The catalog

Only these kinds exist; the launcher starts nothing else. Credentials are fixed and well known
(they exist only inside one scan's network). `{name}` is the service `name` you choose in
`services[]`, which is also its hostname.

| kind | port | seed files | connection |
|---|---|---|---|
| `postgres` | 5432 | yes | `postgresql://app:app@{name}:5432/app` |
| `mysql` | 3306 | yes | `mysql://app:app@{name}:3306/app` |
| `redis` | 6379 | no | `redis://{name}:6379/0` |
| `mongo` | 27017 | no | `mongodb://app:app@{name}:27017/app?authSource=admin` |
| `mailpit` | 1025 | no | `smtp://{name}:1025  (web API for sent mail: http://{name}:8025/api/v1/messages)` |
| `oauth2` | 8080 | no | `issuer http://{name}:8080/default  (any username logs in; claims via the login form)` |

Adapt the URL scheme to the driver: SQLAlchemy wants `postgresql+psycopg://...` or
`mysql+pymysql://...`, JDBC wants `jdbc:postgresql://db:5432/app` with user and password as
separate settings, some apps want host, port, user, password and database as five variables.
A service that never gets healthy is reported in the environment info, not fatal; read the
app log before assuming the service is at fault.

Pick the smallest set: a service is only worth it when the app cannot run, or the bug cannot
show, without that engine. Use the app's sqlite / in-memory option otherwise (see
[env-building](../env-building/SKILL.md)).

## Schema and seed data

Seed data must come from the **repository** or from **EnvSpec commands**; the replay starts
from a clean copy of the source and never sees changes you made by hand.

- **Migrations in `build`.** Services are up before `install` runs, so `build` can migrate and
  seed (`manage.py migrate`, `alembic upgrade head`, `npx prisma migrate deploy`,
  `npm run seed`).
- **Service `seed` files.** For `postgres` and `mysql`, `seed` lists repo-relative `.sql` or
  `.sql.gz` files loaded when the container first initialises, in the order listed. Use them for
  a repository's own `schema.sql` / `seed.sql`. Scripts (`.sh`, `.js`) are never loaded; mongo
  takes no seed files, so seed it through the app or a `build` command. They run before the app's migrations, so do not combine a seed file that creates
  tables with migrations that create the same tables.
- **Inline build commands.** A short script that uses the app's own models and password hasher
  is the most reliable way to create users: the hash format is always right and constraints are
  respected.

Keep seed data minimal and distinctive: object names and notes that cannot occur by accident
(`bob-private-note-7f3a`) make oracles exact.

## Test users, tenants and roles

Authorization bugs need **at least two principals**, created before the PoC runs:

| Bug class | Principals |
|---|---|
| `idor` | `alice` and `bob`, same role, each owning at least one object; in multi-tenant apps put them in **different tenants** |
| `bfla` | a low-privilege user (`mallory`, role `user`) and, if the PoC needs a victim object or a before/after comparison, an `admin` |
| `mass-assignment`, `value-tampering`, `workflow-bypass` | one normal user is usually enough |

Ways to create them, best first:

1. The repository's seed / fixture mechanism, if it creates known credentials.
2. The app's **public sign-up endpoint**, called from the PoC's per-user `login` steps
   (`POST /api/register` then `POST /api/login`). This needs no seeding and works on base and
   head, but only for roles a self-registered user gets.
3. A `build` step that creates users with the app's models (for roles, tenants and admins that
   cannot self-register).

Record username, password and role of every seeded user in the env stage `notes` and use the
same values in the PoC's `users.<name>.vars`. Login steps then use `${USER.username}` and
`${USER.password}`; cookies are kept per user, and `users.<name>.headers` carries tokens
(`Authorization: Bearer ${USER.token}`) extracted by a login step.

**oauth2**: the mock issuer at `http://{name}:8080/default` signs tokens for any username. PoC
steps may only address the app (and canary hosts), so a PoC cannot fetch tokens from the mock
directly; it works when the app performs the login redirect itself. When the app only accepts
bearer tokens from an IdP and has no test login mode, report the hypothesis as `blocked` with
that reason rather than weakening authentication in the EnvSpec.

**Email flows** (sign-up confirmation, password reset): use `mailpit` as SMTP server; the app's
mail goes there instead of the sink. The PoC cannot read mailpit's API either, so prefer flows
where the token is not needed, or an app setting that auto-confirms in development.

## The sink: unknown hosts are recorded, not reached

The workbench resolves every hostname that is not a catalog service or infrastructure to the
**sink**. The app believes it reached `api.stripe.com`; it reached the sink.

- **HTTP (port 80)**: every request is recorded (host, method, path, headers, body up to
  64 KiB) and answered from the EnvSpec `stubs`, else `200 {}`.
- **TLS (port 443)**: the SNI host is recorded and the connection closed. HTTPS calls fail.
  If the code path under test needs the answer, point the client at plain HTTP through its
  base-URL setting and stub it.
- `prsec-canary hits [--contains <s>]` prints what the sink recorded. Check it during authoring
  to see what the app calls at start-up and on your requests: an app that already forwards
  request bodies to an analytics or error-tracking host will make a careless `canary_hit` oracle
  fire (see [oracles](../oracles/SKILL.md)).

## Stubs

A stub matches `host` (exact or glob like `*.stripe.com`), `method` (`*` for any) and
`path_prefix`; the first match answers with `status`, `headers` and `body` (a string; JSON must
be escaped inside the EnvSpec JSON).

```json
{
  "host": "api.payments.example",
  "method": "POST",
  "path_prefix": "/v1/charges",
  "status": 200,
  "headers": {"Content-Type": "application/json"},
  "body": "{\"id\": \"ch_dummy\", \"status\": \"succeeded\", \"amount\": 1200}"
}
```

Write stubs for the calls that decide the code path under test (a payment that must succeed
before an order is confirmed, a feature-flag service that must return `true`, an entitlement
check). Model the provider's real response shape from the client code or SDK types in the
repository. A stub must never make the bug appear: if the vulnerability depends on what the
third party returns, the stub must return what the real provider returns for that input, and
the reasoning must say so.
