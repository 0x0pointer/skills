---
name: env-building
description: Work out how to install, build, seed and start the PR's application inside an isolated workbench and write it down as an EnvSpec - stack, workdir, install/build/start commands, port, health check, environment, mock services and third-party stubs - preferring local sqlite or in-memory options, using catalog services otherwise, and verifying with prsec-env up. Produces the env stage JSON (EnvOutput) and the corrected envspec of the dynamic stage.
---

# Building a runnable environment

Dynamic validation only counts when an **agent-free replay** can start the app from scratch and
run a PoC against it. The EnvSpec you write is the replay's only instructions: every command it
needs to go from a clean checkout to a listening, seeded app must be in it. Nothing you do by
hand during your session survives into the replay.

## Inputs

- `pr.json`, `diff.patch`, `changed_files.txt` and the repository at the PR head (working
  directory, normally `/work/src`).
- `previous_envspec.json` if present: the spec that last brought this repository up healthy.
  Start from it; change only what the PR or the repository now requires, and say what you
  changed in `notes`.
- The catalog of mock services (the prompt shows it; the [mocking](../mocking/SKILL.md) skill
  explains each kind).

## How the spec is executed

1. The repository is copied to a writable app dir; commands run with bash in
   `<app dir>/<workdir>`.
2. `install` then `build` run in order with access to package registries only (pypi, npm,
   Go proxy, Maven Central, Gradle). Nothing else on the internet is reachable.
3. `start` runs in the foreground, in the background of the workbench, with `env` and **no
   proxy**. Every outbound call the app makes lands at the sink (see
   [mocking](../mocking/SKILL.md)), which records it and answers from `stubs`.
4. The app is healthy when `GET http://127.0.0.1:<port><health.path>` returns one of
   `health.expect_status` within `health.timeout_s`.
5. Catalog services are already running and reachable by their `name` before `install` starts,
   so `build` may run migrations and seeds against them.

The same spec is run on the PR head and on the base commit, so do not depend on files that only
the PR adds unless the feature itself needs them.

## Method

### Step 1: Identify the stack and the entry point

Read, in this order: the README / CONTRIBUTING "run locally" section, `Dockerfile` /
`docker-compose*.yml` / `Procfile` (the `CMD` and the compose services are the best summary of
what the app needs), the dependency manifest, then the code that creates the server. Per stack:
[references/python.md](references/python.md), [references/node.md](references/node.md). For Go,
Java and other stacks apply the same questions with `stack: go | java | other`.

Answer for yourself:

- Which framework and which module is the entry point (`app:app`, `manage.py`, `server.js`,
  `dist/main.js`)?
- Which port does it listen on, and is the port taken from an env var (`PORT`)? Pick a fixed
  port (e.g. 8000) and set the variable.
- Which host does it bind? It must be reachable on `127.0.0.1`; `0.0.0.0` is fine too.
- Which environment variables are **required at start-up** (the app crashes without them)?
  Look for `os.environ[...]`, `process.env.X` with no default, settings validation (pydantic
  `BaseSettings`, `envalid`, `convict`, `zod` schemas), `.env.example`.
- Which datastores, caches, queues and third-party APIs does it touch at start-up or on the
  endpoints the PR changes?

### Step 2: Choose the cheapest working backing services

Prefer, in this order:

1. **The app's own local mode**: sqlite file, in-memory database, in-process cache, a
   `TESTING` / `development` setting that disables external integrations. Many apps support
   `DATABASE_URL=sqlite:///./app.db`, `CACHE_BACKEND=memory`, `QUEUE=inline`.
2. **A catalog service** (`postgres`, `mysql`, `redis`, `mongo`, `mailpit`, `oauth2`) when the
   code really depends on that engine (raw SQL with engine-specific syntax, JSONB, Redis
   commands, Mongo queries). For a SQL injection hypothesis use the **same engine** as
   production: payload syntax differs between sqlite, Postgres and MySQL.
3. **A stub** (`stubs[]`) for any third-party HTTP API: payment providers, email APIs, feature
   flag services, webhooks.

Service `name` is the hostname the app connects to (`db`, `cache`), lowercase, never `sink`,
`llm-gateway`, `egress-proxy`, `localhost` or `app`. Write connection strings with the service
name as host and the catalog's fixed credentials, e.g. `postgresql://app:app@db:5432/app`.

### Step 3: Schema, migrations and seed data

The app must start with its schema in place and with the data a PoC needs (at least two users
for authorization bugs; a role-holding user for function-level bugs; the objects the endpoint
reads). Options, best first:

- The app's migration command in `build` (`python manage.py migrate`, `alembic upgrade head`,
  `npx prisma migrate deploy`, `npm run migrate`).
- The app's own seed / fixture command (`manage.py loaddata`, `npm run seed`, a seed script
  the README mentions).
- An inline `build` command that creates users through the app's own models and password
  hasher (`.venv/bin/python -c "..."`), so password hashes are always in the right format.
- Repo-relative `.sql` / `.sql.gz` seed files listed in a service's `seed` (postgres and mysql
  only; see [mocking](../mocking/SKILL.md)).

Details on users, tenants and roles are in [mocking](../mocking/SKILL.md). Record every seeded
credential in `notes` so the PoC author can use it.

### Step 4: Stubs for third-party APIs

The sink answers plain HTTP from `stubs` and otherwise returns `200 {}`. It cannot answer HTTPS:
a TLS connection is recorded and closed. When the app calls an HTTPS API that matters for the
code under test, point it at plain HTTP through configuration (`STRIPE_API_BASE=http://api.stripe.com`,
`PAYMENTS_URL=http://payments.example`) and add a stub for that host and path with a realistic
body. When the call does not matter, prefer the app's switch that disables the integration.
Never put real credentials in `env`; use obvious dummies (`sk_test_dummy`).

### Step 5: Verify

When `prsec-env` is available in your stage, verify the spec instead of guessing:

```bash
prsec-env up --spec envspec.json     # install, build, start, wait for health
prsec-env status                     # healthy / unhealthy / stopped
prsec-env logs -n 200                # app log tail (start-up errors, stack traces)
prsec-env reset                      # fresh copy and clean state, then up again
prsec-env down
```

Fix one failure at a time from the log: missing env var, wrong module path, port mismatch,
migration ordering, a dependency that needs a system library. If install cannot work (private
registry, unavailable system packages), say so in `notes`; the dynamic stage will report
`env_failed` or `blocked` rather than invent an environment. In the env stage there may be no
registry access and no services; then write the spec from reading alone and mark every guess
in `notes`. The dynamic stage starts it and corrects commands, env and stubs (it may not change
`services`, so get those right here).

### Health check

Pick a path that proves **this app** is up: a health route, or an authenticated route that
answers `401` (`expect_status: [401]`). The default accepts any status 200-499 on `/`, which is
fine for most apps. Keep `timeout_s` realistic (Java and large Node builds: 300+).

## Output (env stage JSON)

```json
{
  "envspec": {
    "stack": "python",
    "workdir": ".",
    "install": ["python -m venv .venv", ".venv/bin/pip install -r requirements.txt"],
    "build": [".venv/bin/python manage.py migrate --noinput", ".venv/bin/python manage.py loaddata dev_users"],
    "start": ".venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload",
    "port": 8000,
    "health": {"path": "/api/me", "expect_status": [401, 403], "timeout_s": 120},
    "env": {
      "DJANGO_SETTINGS_MODULE": "shop.settings",
      "DATABASE_URL": "postgresql://app:app@db:5432/app",
      "REDIS_URL": "redis://cache:6379/0",
      "SECRET_KEY": "prsec-dummy-secret",
      "PAYMENTS_API_BASE": "http://payments.example"
    },
    "services": [{"name": "db", "kind": "postgres", "seed": []}, {"name": "cache", "kind": "redis", "seed": []}],
    "stubs": [
      {"host": "payments.example", "method": "POST", "path_prefix": "/v1/charges", "status": 200,
       "headers": {"Content-Type": "application/json"}, "body": "{\"id\": \"ch_dummy\", \"status\": \"succeeded\"}"}
    ],
    "install_timeout_s": 900
  },
  "notes": "Django 5 app (manage.py, settings in shop/settings.py). Uses Postgres-specific JSONB queries, so postgres instead of sqlite. Fixture dev_users seeds alice/alice-pass and bob/bob-pass (role customer) and admin/admin-pass (staff). Payment client reads PAYMENTS_API_BASE; stubbed. Guess, not verified: Celery is not needed because the changed endpoint does not enqueue tasks."
}
```

In the dynamic stage, put the corrected spec in the `envspec` field of your output only when you
had to change it, and keep the env stage's `services` unchanged.
