# Node.js: Express, Nest, Fastify, Next.js API routes

## Sources

| Framework | Attacker-controlled |
|---|---|
| Express / Fastify | `req.query`, `req.params`, `req.body`, `req.headers`, `req.cookies`, `req.get(...)`, `req.hostname`, `req.ip` (spoofable behind `trust proxy`), `req.files` / multer `file.originalname`, `file.buffer` |
| Nest | `@Query()`, `@Param()`, `@Body()`, `@Headers()`, `@Req()`, `@UploadedFile()`, GraphQL `@Args()`, microservice `@Payload()`, `@MessagePattern` / `@EventPattern` handlers |
| Next.js | `req.query` / `req.body` in API routes, `params` / `searchParams` in route handlers and server components, server action arguments (callable by anyone) |
| Other | WebSocket `message` handlers, queue consumers (`channel.consume`, `kafkajs` `eachMessage`), webhook bodies, `fetch` responses from third parties, rows written earlier by other users |

Express `req.query` values can be **arrays or objects** (`?a[]=1`, `?a[$ne]=x` with the default
`qs` parser). Type confusion is a frequent root cause of NoSQL injection and validation bypass.

## Sinks and their safe variants

| Bug class | Dangerous | Usually safe |
|---|---|---|
| sqli | `` db.query(`... ${x}`) ``, `sequelize.query(str)` with interpolation, `knex.raw(str + x)`, `prisma.$queryRawUnsafe(str)`, TypeORM `.query(str)` / `.where("a = " + x)` | `db.query(sql, [x])`, `knex.raw('?', [x])`, `prisma.$queryRaw` tagged template, TypeORM `.where("a = :x", { x })`, ORM finders |
| nosqli | Mongoose/Mongo `find(req.body)`, `{ field: req.query.x }` where `x` may be an object, `$where`, `$expr` with input, `mapReduce` | casting to string (`String(x)`), schema validation that rejects objects, `mongo-sanitize` / `sanitizeFilter: true` |
| cmdi | `child_process.exec(str)`, `execSync`, `spawn(cmd, { shell: true })`, `shelljs.exec` | `execFile` / `spawn` with argv array and no shell (still check option injection like `--output=`) |
| code-injection | `eval`, `new Function`, `vm.runInNewContext` (not a sandbox), `setTimeout(string)` | none with input; refactor |
| path-traversal | `fs.*(path.join(base, x))`, `res.sendFile(x)`, `res.download(x)`, `express.static` with user-chosen root, archive extraction (`adm-zip`, `tar`) | `path.resolve(base, x)` followed by a `startsWith(base + path.sep)` check; `res.sendFile(name, { root })` (blocks `..` but not absolute paths in old versions) |
| ssrf | `axios(x)`, `fetch(x)`, `got(x)`, `http.request(x)`, `needle`, headless browser `page.goto(x)` | hostname allowlist checked on the **resolved** address, redirects disabled or re-checked |
| xss | `res.send(userHtml)`, template raw output: EJS `<%- %>`, Pug `!=`, Handlebars `{{{ }}}`, React `dangerouslySetInnerHTML`, Vue `v-html`, Angular `bypassSecurityTrust*` | EJS `<%= %>`, Handlebars `{{ }}`, React JSX text, DOMPurify on the final HTML |
| ssti | `ejs.render(userTemplate)`, `pug.compile(x)`, `Handlebars.compile(x)`, `nunjucks.renderString(x)` | rendering a fixed template with user data |
| deserialization | `node-serialize.unserialize`, `serialize-javascript` round trips into `eval`, `js-yaml.load` with old versions / unsafe schema | `JSON.parse`, `yaml.load` with `JSON_SCHEMA` / js-yaml >= 4 default |
| prototype-pollution | recursive merge / `lodash.merge`, `_.set`, `defaultsDeep`, `Object.assign` of nested parsed JSON with `__proto__` / `constructor.prototype` keys | `Object.create(null)` targets, key denylist, `structuredClone`, schema validation |
| open-redirect | `res.redirect(req.query.next)` | relative-path-only check, allowlist |
| header-injection | `res.setHeader(name, x)` with CR/LF (modern Node rejects CRLF; check custom raw sockets) | built-in validation |
| crypto-misuse | `Math.random()` for tokens, `crypto.createCipher` (no IV), `md5`/`sha1` for passwords, `jwt.verify` without `algorithms`, `jwt.decode` used as verify | `crypto.randomBytes`, `bcrypt`/`argon2`, `jwt.verify(t, key, { algorithms: [...] })` |
| mass-assignment | `Model.create(req.body)`, `findByIdAndUpdate(id, req.body)`, `Object.assign(entity, req.body)`, Sequelize `update(req.body)` without `fields` | explicit pick of allowed fields, DTO with `whitelist: true, forbidNonWhitelisted: true` (Nest `ValidationPipe`) |

## Propagation and sanitisers

- Template literals, `+`, `concat`, `util.format`, `Array.join` all propagate taint.
- `parseInt(x, 10)` / `Number(x)` + `Number.isInteger` neutralise injection into numeric
  contexts (`NaN` handling may still matter). `encodeURIComponent` neutralises injection into a
  URL path segment, not into a full URL (SSRF) and not into HTML.
- Validation libraries (`joi`, `zod`, `yup`, `class-validator`, `express-validator`, `ajv`) only
  count if the handler uses the **validated output** and the schema constrains the dangerous
  property (type `string` alone does not stop SQLi).
- Nest `ValidationPipe` is global only if registered in `main.ts` (`app.useGlobalPipes`) or via
  `APP_PIPE`; check before relying on it.

## Auth and framework protections

- Express: middleware order matters. A route registered **before** `app.use(authMiddleware)` is
  unauthenticated. Check `router.use` scoping and route-level middleware arrays.
- Nest: `@UseGuards(...)` per controller/handler, global guards via `APP_GUARD`, and
  `@Public()`-style decorators that skip guards. A new handler on a guarded controller inherits
  the guard; a new controller does not.
- Next.js: `middleware.ts` `matcher` patterns decide coverage; server actions are public
  endpoints regardless of which page imports them.
- CSRF: cookie-session apps need `csurf`-style tokens or `SameSite` cookies; token-in-header APIs
  are not CSRF-prone.
