# Python: Django, DRF, Flask, FastAPI

## Sources

| Framework | Attacker-controlled |
|---|---|
| Django / DRF | `request.GET`, `request.POST`, `request.body`, `request.data`, `request.query_params`, `request.FILES` (name and content), `request.headers` / `request.META['HTTP_*']`, `request.COOKIES`, URL kwargs, serializer `validated_data` (validated, still attacker data) |
| Flask | `request.args`, `request.form`, `request.values`, `request.json` / `get_json()`, `request.data`, `request.files`, `request.headers`, `request.cookies`, view arguments from the route |
| FastAPI / Starlette | path, query, header, cookie and body parameters, Pydantic models (types enforced; strings are still arbitrary), `Request` object, `UploadFile.filename` |
| Other | Celery / RQ task arguments that originate from requests, Kafka / SQS consumers, webhook payloads, `requests` responses from third parties, rows written by other users |

## Sinks and their safe variants

| Bug class | Dangerous | Usually safe |
|---|---|---|
| sqli | `cursor.execute(f"...{x}")`, `% x` / `.format(x)` / `+ x` into SQL, Django `.raw(str)`, `.extra(where=[str])`, `RawSQL(str)`, SQLAlchemy `text(f"...")`, `session.execute(str)` | `cursor.execute(sql, (x,))`, `.raw(sql, [x])`, `text("... :x").bindparams(x=x)`, ORM filters |
| sqli (identifiers) | user-chosen `order_by(x)`, column or table names interpolated even in otherwise bound queries | allowlist of column names |
| nosqli | `pymongo` `find(request.json)`, `$where`, operator dicts from JSON input | casting to `str`, Pydantic model with `str` fields |
| cmdi | `os.system`, `os.popen`, `subprocess.*(str, shell=True)`, `commands`, `pexpect.spawn(str)` | `subprocess.run([...])` argv list without shell; `shlex.quote` when a shell is unavoidable |
| code-injection | `eval`, `exec`, `compile`, `pandas.eval` / `DataFrame.query` with input, `importlib.import_module(x)` | `ast.literal_eval` for literals only |
| path-traversal | `open(os.path.join(base, x))`, `send_file(x)`, `send_from_directory` with user-controlled directory, `FileResponse(x)`, `zipfile.extractall` / `tarfile.extractall` without filter | `werkzeug.utils.secure_filename`, `safe_join`, `Path(base, x).resolve().is_relative_to(base)`, `tarfile` `filter="data"` |
| ssrf | `requests.get(x)`, `httpx`, `urllib.request.urlopen(x)` (also `file://`), `aiohttp` | allowlist on resolved IP, `allow_redirects=False` or re-validation |
| xss | Django `mark_safe(x)`, `|safe`, `{% autoescape off %}`, `format_html` misuse (passing pre-joined strings), Jinja2 `Environment(autoescape=False)` (default outside Flask), `Markup(x)`, returning `HTMLResponse(x)` | Django templates (autoescape on), Flask `render_template` with `.html` templates, `bleach`/`nh3` on the final HTML |
| ssti | `render_template_string(x)`, `Template(x).render()`, `Environment().from_string(x)`, Django `Template(x)` | fixed template + user data in context; `SandboxedEnvironment` reduces but does not remove risk |
| deserialization | `pickle.loads`, `cPickle`, `dill`, `joblib.load`, `shelve`, `yaml.load` without `SafeLoader` / `yaml.unsafe_load`, `jsonpickle.decode`, `numpy.load(allow_pickle=True)` | `json.loads`, `yaml.safe_load` |
| xxe | `lxml.etree.parse` with `resolve_entities=True` (older default), `xml.dom.minidom` / `sax` with external entities enabled | `defusedxml` |
| open-redirect | `redirect(request.args["next"])`, `HttpResponseRedirect(x)` | `url_has_allowed_host_and_scheme(x, allowed_hosts)` |
| crypto-misuse | `random.*` for tokens, `hashlib.md5/sha1` for passwords, `jwt.decode(t, options={"verify_signature": False})` or without `algorithms=`, `==` compare of MACs | `secrets.*`, Django hashers / `passlib` / `argon2`, `hmac.compare_digest` |
| mass-assignment | `Model(**request.json)`, `obj.__dict__.update(data)`, `setattr` loops over input keys, DRF `ModelSerializer` with `fields="__all__"` and no `read_only_fields`, Django `ModelForm` `fields="__all__"` | explicit field lists, separate input schemas (Pydantic `Create` vs `DB` models) |

## Propagation and sanitisers

- f-strings, `%`, `.format`, `+`, `"".join` propagate. `int(x)` / `uuid.UUID(x)` neutralise
  injection (watch for the exception path: an unhandled `ValueError` is a 500, not a bypass).
- Pydantic / DRF serializers constrain **types**; `constr(pattern=...)`, `Literal[...]`, enums
  and `conint` constrain values. A plain `str` field accepts any payload.
- `django.utils.html.escape` and `markupsafe.escape` are HTML-context escapes only; they do not
  help in JavaScript, URL or SQL contexts.

## Auth and framework protections

- Django: `@login_required`, `LoginRequiredMixin`, `@permission_required`, DRF
  `permission_classes` (per view) and `DEFAULT_PERMISSION_CLASSES` (settings). A view with
  `permission_classes = []` or `AllowAny` overrides the default. Object permissions in DRF only
  run when `get_object()` is used; custom `get_queryset()` must filter by owner itself.
- Django CSRF is on by default for session auth; `@csrf_exempt` disables it.
- Flask: no auth by default; look for `@login_required` (Flask-Login), `before_request` hooks
  and blueprint-level hooks. A new blueprint does not inherit another blueprint's hooks.
- FastAPI: auth is a dependency (`Depends(get_current_user)`) on the route, router
  (`APIRouter(dependencies=[...])`) or app. A route without it is public. `Security(...)` scopes
  only matter if the dependency actually checks them.
