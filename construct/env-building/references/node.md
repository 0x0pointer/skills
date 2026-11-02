# Node.js: Express, Fastify, Koa, NestJS, Next.js

## Find the stack

| Signal | Means |
|---|---|
| `package-lock.json` | `npm ci` |
| `yarn.lock` | `corepack enable && yarn install --frozen-lockfile` (Yarn 1) or `yarn install --immutable` (Berry) |
| `pnpm-lock.yaml` | `corepack enable && pnpm install --frozen-lockfile` |
| `"type": "module"` | ESM: start with `node file.js`, not `require` tricks |
| `tsconfig.json` + `"build"` script | TypeScript: `npm run build` in `build`, start the compiled output (`node dist/main.js`) |
| `@nestjs/core` | NestJS: `npm run build`, then `node dist/main.js` |
| `next` | Next.js: `npx next build` then `npx next start -H 127.0.0.1 -p 3000` |
| `express()`, `fastify()`, `new Koa()` | find the file that calls `.listen(...)` |

Read `package.json` `scripts.start`, `main`, and the `Dockerfile` `CMD`. Prefer running the
built output with `node` over `npm run dev`: watchers (`nodemon`, `ts-node-dev`, `next dev`)
restart on file changes and compile lazily, which makes health checks and replays flaky.
Workspaces / monorepos: set `workdir` to the package that holds the server and install from the
root only when the lockfile lives there (then `workdir` stays `.` and `start` uses
`npm --workspace <pkg> run start` or `node packages/api/dist/main.js`).

## Port and host

Most apps read `process.env.PORT` (and sometimes `HOST`). Set both in `env`
(`PORT=3000`, `HOST=127.0.0.1`) and use the same value as `port`. If the port is hardcoded, use
it. Fastify defaults to binding `127.0.0.1`, which is fine.

## Databases

| ORM / driver | Local option | Schema / seed |
|---|---|---|
| Prisma | provider is fixed in `schema.prisma`; sqlite only if it already says `sqlite` | `npx prisma migrate deploy` (or `npx prisma db push` with no migrations), `npx prisma db seed` |
| Sequelize | `dialect: 'sqlite'`, `storage: './app.sqlite'` when config is env-driven | `npx sequelize-cli db:migrate`, `db:seed:all` |
| TypeORM | `type: 'better-sqlite3'` when the data source reads env | `npm run migration:run` or `synchronize` in development config |
| Knex | `client: 'better-sqlite3'` when the knexfile has a development entry | `npx knex migrate:latest`, `npx knex seed:run` |
| Mongoose | none: use the `mongo` catalog service | the app's seed script (mongo takes no seed files) |
| `pg`, `mysql2` raw | none: use `postgres` / `mysql` | SQL files in the repo as service `seed`, or the migration script |

Connection strings use the service name as host: `postgresql://app:app@db:5432/app`,
`mongodb://app:app@mongo:27017/app?authSource=admin`, `redis://cache:6379/0`.

## Seed users

Use the repository's seed script when it creates known credentials. Otherwise add a `build`
step that calls the app's own user service or model with its hashing library, e.g.
`node -e "require('./dist/seed-users.js')"` if such a module exists, or a short inline script
that requires the ORM client and `bcrypt` and inserts two users and an admin. Print nothing
secret; record the credentials in `notes`.

## Environment

`NODE_ENV=development` (or `test` if that switches integrations off; avoid `production` when it
forces HTTPS-only cookies, which a plain-HTTP PoC cannot send back). Dummy values for
`JWT_SECRET`, `SESSION_SECRET`, API keys. Check `.env.example` and config validators (`envalid`,
`joi`, `zod`) for every required variable; apps using `dotenv` read `.env` from the workdir, but
put values in `env` instead of writing files.

## Common failures

| Log says | Fix |
|---|---|
| `Cannot find module 'dist/...'` | build step missing or wrong output dir (`outDir` in `tsconfig.json`) |
| `EADDRINUSE` | another process from an earlier `up`; `prsec-env reset` |
| `ECONNREFUSED 127.0.0.1:5432` | the app defaults to localhost: set the URL variable to the service name |
| `node-gyp` / native module build errors | prefer the pure-JS alternative if the code allows; otherwise report `blocked` |
| `secure cookie` set but never sent back | `NODE_ENV=production` or `cookie.secure: true`; use a non-production setting |
