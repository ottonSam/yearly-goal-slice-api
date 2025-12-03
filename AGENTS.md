# Repository Guidelines

## Project Structure & Modules
- Django project managed via `manage.py` with settings in `yearly_goal_slice/` (asgi/wsgi, fields, urls, settings).
- Domain apps: `accounts` (UUID user + auth), `goal_calendars` (weekly goals, activities, progress), `objectives` (long/medium/calendar objectives).
- Each app keeps `models.py`, `serializers.py`, `views.py`, `urls.py`, `tests.py`, and `migrations/`; dependencies pinned in `requeriments.txt`.
- Local SQLite DB lives in `db.sqlite3` (created by migrations); docs exposed at `/swagger/` and `/redoc/` once running.

## Setup, Build & Run
- Create env: `python3 -m venv .venv && source .venv/bin/activate`.
- Install deps: `pip install -r requeriments.txt`.
- Apply schema: `source .venv/bin/activate && python manage.py migrate`; create admin (optional): `source .venv/bin/activate && python manage.py createsuperuser`.
- Start API: `source .venv/bin/activate && python manage.py runserver` (dev server on `http://localhost:8000`).

## Coding Style & Naming
- Python + Django REST: follow PEP 8 (4-space indent, snake_case for vars/functions, PascalCase for classes).
- Keep serializers/viewsets lean; push business rules to models/services when possible. Use DRF `Response` + status codes; keep UUID primary keys consistent with existing models.
- URL patterns stay grouped per app under `/api/v1/`; name files and symbols after the domain noun (e.g., `GoalCalendarSerializer`, `ObjectiveViewSet`).

## Testing Guidelines
- Tests co-located in each app’s `tests.py`; name cases `test_<behavior>`.
- Run all: `source .venv/bin/activate && python manage.py test`; target happy-path and edge cases for JWT auth, calendar activity progress, and objective validations.
- Prefer `APIClient` for REST flows; assert status codes and payload fields; add regression tests with clear fixture/setup steps.

## Commit & PR Guidelines
- Follow current history style (`feat: …`, `fix: …`, `docs: …`); keep commits small and scoped. Include migrations when models change.
- PRs should state purpose, endpoints touched, migration impact, and how to test (commands + sample payloads). Add screenshots for API doc changes when relevant.
- Rebase onto the main branch before opening; ensure lint/tests pass locally.

## Security & Config Notes
- Do not commit secrets; store local settings in an untracked `.env`. JWT keys/DB paths configurable via Django settings; default dev DB is SQLite.
- Protect `/api/v1/` calls with JWT from `/auth/login/` and refresh via `/auth/refresh/`; use an admin user for `/admin/`.
