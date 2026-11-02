# PHP: plain PHP, Laravel, Symfony, WordPress

## Sources

- Superglobals: `$_GET`, `$_POST`, `$_REQUEST`, `$_COOKIE`, `$_FILES` (`name`, `type` are
  attacker-chosen), `$_SERVER['HTTP_*']`, `$_SERVER['REQUEST_URI']`, `PHP_SELF`,
  `php://input`.
- Laravel: `$request->input()`, `->query()`, `->all()`, `->get()`, route parameters,
  `$request->file()`, Form Request `validated()` (validated, still attacker data).
- Symfony: `$request->query`, `->request`, `->attributes`, `->headers`, `->cookies`,
  `->getContent()`, `#[MapRequestPayload]` DTOs.
- WordPress: `$_GET`/`$_POST` in `admin-ajax` / REST callbacks, shortcode attributes.

## Sinks and their safe variants

| Bug class | Dangerous | Usually safe |
|---|---|---|
| sqli | `mysqli_query($c, "..." . $x)`, `$pdo->query("... $x")`, Laravel `DB::raw($x)`, `whereRaw($x)`, `orderByRaw`, `selectRaw` with interpolation, Doctrine `createQuery("... $x")`, `$wpdb->query("... $x")` | PDO prepared statements, `whereRaw('a = ?', [$x])`, query builder, Doctrine parameters, `$wpdb->prepare` |
| sqli (identifiers) | `orderBy($request->sort)`, column names from input | allowlist |
| cmdi | `system`, `exec`, `shell_exec`, backticks, `passthru`, `popen`, `proc_open` with a string, `mail()` fifth parameter | `escapeshellarg` per argument, `Symfony\Process` with array |
| code-injection | `eval`, `assert($x)` (PHP < 8), `create_function`, `preg_replace` with `/e`, `call_user_func($x)` / variable functions `$x()` with input, `include $x` / `require $x` | allowlist |
| path-traversal | `file_get_contents($x)`, `fopen`, `readfile`, `include`, `unlink`, `move_uploaded_file` to a user-chosen name, Laravel `Storage::get($x)`, `response()->download($x)` | `basename($x)`, `realpath` + prefix check |
| ssrf | `file_get_contents($url)`, `curl_exec` with user `CURLOPT_URL`, Guzzle with user URI, `fopen` with wrappers (`php://`, `phar://`, `gopher://` via curl) | allowlist + scheme restriction (`CURLOPT_PROTOCOLS`) |
| xss | `echo $x`, `<?= $x ?>`, Blade `{!! $x !!}`, Twig `|raw`, `{% autoescape false %}` | Blade `{{ }}`, Twig default, `htmlspecialchars($x, ENT_QUOTES)`, `esc_html` / `esc_attr` |
| ssti | Twig `createTemplate($x)`, `Environment::render` of user-provided template source, Blade `Blade::render($x)` | fixed templates |
| deserialization | `unserialize($x)`, `phar://` paths reaching any filesystem function (implicit unserialize on PHP < 8), `maybe_unserialize` | `json_decode`, `unserialize($x, ['allowed_classes' => false])` |
| xxe | `simplexml_load_string` / `DOMDocument::loadXML` with `LIBXML_NOENT` or `LIBXML_DTDLOAD` | libxml >= 2.9 defaults without those flags |
| open-redirect | `header("Location: " . $x)`, `redirect($x)` / `redirect()->to($x)` | `redirect()->route(...)`, allowlist |
| header-injection | `header($x)` with CR/LF (PHP blocks multiple headers since 5.1.2; check old runtimes) | |
| crypto-misuse | `rand`, `mt_rand`, `uniqid` for tokens, `md5($password)`, `sha1`, `==` on hashes (type juggling: `"0e123" == "0e456"`), `strcmp` on arrays | `random_bytes`, `password_hash` / `password_verify`, `hash_equals` |
| mass-assignment | Eloquent `Model::create($request->all())`, `->fill($request->all())`, `->update($request->all())` with `$guarded = []` or missing `$fillable`; Doctrine forms with all fields | `$fillable` allowlists, `$request->validated()` / `->only([...])` |

## Propagation and sanitisers

- `.` concatenation, double-quoted string interpolation, `sprintf`, `implode` propagate.
- Loose comparison (`==`, `in_array` without strict flag, `switch`) enables type-juggling bypasses
  of checks; JSON input can supply booleans, integers and arrays.
- `addslashes` and `mysqli_real_escape_string` are fragile (charset issues, numeric contexts
  without quotes); `intval` neutralises numeric contexts. `strip_tags` is not an XSS defence for
  attribute contexts.

## Auth and framework protections

- Laravel: `auth` / `auth:sanctum` middleware on routes or groups (`routes/api.php`,
  `routes/web.php`), `Gate::allows`, policies (`$this->authorize('update', $post)`), route model
  binding (does not check ownership by itself). CSRF via `VerifyCsrfToken` with `$except` list.
- Symfony: `security.yaml` `access_control` (first match wins), `#[IsGranted]`, voters.
- WordPress: `current_user_can()`, nonces (`check_ajax_referer`, `wp_verify_nonce`);
  `wp_ajax_nopriv_*` hooks are unauthenticated.
