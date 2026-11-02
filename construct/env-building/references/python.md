# Python: Flask, Django, FastAPI

## Find the stack

| Signal | Means |
|---|---|
| `requirements*.txt` | `pip install -r requirements.txt` (dev file only if the app needs it to start) |
| `pyproject.toml` with `[tool.poetry]` | `pip install poetry && poetry install --no-root` or, simpler, `pip install .` when it is a normal PEP 621 project |
| `pyproject.toml` with `[project]` and `uv.lock` | `pip install uv && uv sync --frozen`, run with `.venv/bin/...` |
| `Pipfile.lock` | `pip install pipenv && pipenv install --deploy` |
| `manage.py` | Django |
| `Flask(__name__)`, `create_app()` | Flask (app object or factory) |
| `FastAPI()`, `uvicorn.run` | FastAPI / Starlette |

Always install into a venv inside the app dir: `python -m venv .venv` then `.venv/bin/pip ...`.
Pin nothing yourself; use the repository's lock or requirements file.

## Start commands

| Framework | start | Notes |
|---|---|---|
| Flask (module object) | `.venv/bin/flask --app app run --host 127.0.0.1 --port 5000` | `--app pkg:create_app()` for a factory; never `--debug` (the reloader forks and the debugger is an RCE surface) |
| Django | `.venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload` | set `DJANGO_SETTINGS_MODULE` if `manage.py` does not; `ALLOWED_HOSTS` must accept `127.0.0.1` |
| FastAPI | `.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000` | find the module that defines `app = FastAPI(...)` |
| gunicorn in Procfile | `.venv/bin/gunicorn -b 127.0.0.1:8000 -w 1 module:app` | one worker keeps state (in-memory stores) consistent |

## Databases

- **sqlite first** when the app reads `DATABASE_URL` / `SQLALCHEMY_DATABASE_URI` and uses only
  portable ORM queries: `DATABASE_URL=sqlite:///./app.db`. Django with `dj-database-url` accepts
  the same URL; otherwise check `DATABASES` in settings for an env switch.
- Use the `postgres` or `mysql` catalog service when the code uses raw SQL, JSONB, `ARRAY`,
  `ON CONFLICT`, full-text search or a driver-only import (`psycopg`, `asyncpg`, `pymysql`), and
  always for SQL injection hypotheses in raw SQL.
- Schema: `manage.py migrate --noinput`, `alembic upgrade head`, `flask db upgrade`
  (Flask-Migrate), or an `init_db.py` / `schema.sql` the README mentions. SQLAlchemy apps
  without migrations often call `db.create_all()` in a CLI command or at start-up.

## Seed users

- Django: `manage.py loaddata <fixture>` when a fixture exists; otherwise
  `DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_PASSWORD=admin-pass DJANGO_SUPERUSER_EMAIL=admin@example.test manage.py createsuperuser --noinput`
  for an admin and a short `manage.py shell -c "..."` that calls `User.objects.create_user(...)`
  for normal users.
- Flask / FastAPI: call the repository's own user-creation helper or model with its password
  hasher in a `.venv/bin/python -c "..."` build step, inside the app context for Flask
  (`from app import app, db; app.app_context().push(); ...`).

## Environment

`SECRET_KEY` / `JWT_SECRET` (dummy value), `DEBUG=0`, `FLASK_ENV` unset, `ENV=development` or
`test` when that disables external integrations. Settings classes (`pydantic-settings`) list
every required variable with its type; satisfy all of them.

## Common failures

| Log says | Fix |
|---|---|
| `ModuleNotFoundError` for the app module | wrong `workdir` or module path; check where the package root is |
| `KeyError: 'X'` / `ValidationError` on settings | add the variable to `env` |
| `could not translate host name "postgres"` | the code hardcodes a host: name the service exactly that, or set the URL variable |
| `no such table` | migrations / `create_all` missing from `build` |
| `Building wheel ... failed` (psycopg2, lxml) | install commands may rewrite the copy: `sed -i 's/^psycopg2==/psycopg2-binary==/' requirements.txt` before `pip install`; otherwise report `blocked` |
