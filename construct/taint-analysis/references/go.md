# Go: net/http, chi, gin, echo, fiber, gRPC

## Sources

- `net/http`: `r.URL.Query()`, `r.FormValue`, `r.PostFormValue`, `r.Form`, `r.Body`
  (decoded via `json.NewDecoder`), `r.Header.Get`, `r.Cookie`, `r.URL.Path`, `r.PathValue`
  (Go 1.22 patterns), `r.MultipartForm` / `FormFile` (header `Filename`).
- Routers: chi `chi.URLParam`, gin `c.Param / c.Query / c.PostForm / c.ShouldBind*`, echo
  `c.Param / c.QueryParam / c.Bind`, fiber `c.Params / c.Query / c.BodyParser`.
- gRPC: every field of the request message; metadata from `metadata.FromIncomingContext`.
- Consumers: Kafka/NATS/SQS message bodies; HTTP responses from third parties.

## Sinks and their safe variants

| Bug class | Dangerous | Usually safe |
|---|---|---|
| sqli | `db.Query(fmt.Sprintf("... %s", x))`, `db.Exec("..." + x)`, gorm `Where(fmt.Sprintf(...))`, `Raw(str)`, `Order(x)`, `Select(x)` / `Group(x)` with input, sqlx `Select(&v, str+x)` | `db.Query("... $1", x)`, gorm `Where("name = ?", x)`, sqlc-generated queries |
| cmdi | `exec.Command("sh", "-c", str)`, `exec.Command("bash", "-c", ...)` | `exec.Command(bin, args...)` with fixed `bin` (check argument / option injection) |
| path-traversal | `os.Open(filepath.Join(base, x))` (Join cleans but does not contain), `http.ServeFile(w, r, x)`, `archive/zip` extraction using `f.Name` | `filepath.Rel` or `strings.HasPrefix(filepath.Clean(p), base+string(os.PathSeparator))`, `os.Root` (Go 1.24), `http.FileServer(http.Dir(base))` |
| ssrf | `http.Get(x)`, `http.NewRequest(m, x, ...)`, `client.Do` with user URL, custom `Dialer` without IP checks | allowlist; `net.Dialer.Control` that rejects private ranges at connect time |
| xss | `text/template` used for HTML, `template.HTML(x)`, `template.JS(x)`, `w.Write([]byte(userHTML))` with `text/html` content type | `html/template` (contextual escaping) with plain strings |
| ssti | `template.New("").Parse(x)` with input as template text | fixed templates |
| deserialization | `encoding/gob` from untrusted peers into interface types, `yaml.Unmarshal` into `interface{}` then reflective dispatch | JSON into concrete structs |
| xxe | rarely applicable: `encoding/xml` does not resolve external entities | n/a |
| open-redirect | `http.Redirect(w, r, r.URL.Query().Get("next"), 302)` | relative-only check (beware `//host` and `/\host`) |
| crypto-misuse | `math/rand` for tokens, `md5` / `sha1` for passwords, `InsecureSkipVerify: true`, `jwt.Parse` keyfunc that does not check `token.Method` | `crypto/rand`, `bcrypt`, `jwt.WithValidMethods` |
| mass-assignment | `c.Bind(&model)` / `json.Decode(&model)` directly into a DB model then `db.Save(&model)`; gorm `Updates(map from input)` | separate request struct with only writable fields |

## Propagation and sanitisers

- `fmt.Sprintf`, `+`, `strings.Join`, `strings.Builder`, `bytes.Buffer` propagate.
- `strconv.Atoi` / `ParseInt`, `uuid.Parse` neutralise for that value **if the error is
  checked**; a discarded error (`id, _ := strconv.Atoi(x)`) yields 0, which can turn into
  "first row" or "all rows" behaviour.
- Struct tags for validation (`validate:"..."` with go-playground/validator, gin `binding:"..."`)
  only apply when the validator is actually invoked (`ShouldBind*` with tags, or explicit
  `validate.Struct`).

## Auth and framework protections

- Middleware is wired explicitly: `r.Use(...)`, `r.Group(func(r chi.Router) { r.Use(auth) ... })`,
  gin `group.Use(...)`. A route registered on the root router instead of the authenticated group
  is public; check where the new route is mounted.
- gRPC: unary/stream interceptors (`grpc.UnaryInterceptor`) apply globally; method allowlists
  inside interceptors (`if info.FullMethod == ...`) often skip auth for named methods.
- Context values (`ctx.Value(userKey)`) carry identity; a nil check that falls through is a
  fail-open.
