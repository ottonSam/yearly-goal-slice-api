Yearly Goal Slice API
=====================

API Django/DRF para gestao de metas anuais com ciclos semanais, objetivos e controle financeiro por carteira (`wallets`), com autenticacao JWT e documentacao Swagger/Redoc.

Stack principal
---------------
- Python `>=3.10`
- Django `4.2.16`
- Django REST Framework `3.16.1`
- SimpleJWT `5.4.0`
- drf-yasg `1.21.7`
- django-cors-headers `4.4.0`

Estrutura de modulos
--------------------
- `accounts`: cadastro/autenticacao, verificacao de email e perfil.
- `goal_calendars`: calendarios, semanas, atividades e progresso semanal.
- `objectives`: objetivos por tipo e por calendario.
- `wallets`: carteiras, categorias, ciclos de fatura, despesas, recorrencias e parcelamentos.

Como rodar localmente
---------------------
1. Instale o `uv` (se necessario): `pip install uv`
2. Crie e ative o ambiente virtual:
   - `uv venv .venv`
   - `source .venv/bin/activate`
3. Instale dependencias: `uv sync`
4. Aplique migracoes: `python manage.py migrate`
5. (Opcional) Crie superuser: `python manage.py createsuperuser`
6. Suba a API: `python manage.py runserver`

Documentacao local
------------------
- Swagger UI: `http://localhost:8000/swagger/`
- Redoc: `http://localhost:8000/redoc/`
- Admin: `http://localhost:8000/admin/`

Variaveis de ambiente importantes
---------------------------------
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_DB_ENGINE`, `DJANGO_DB_NAME`, `DJANGO_DB_USER`, `DJANGO_DB_PASSWORD`, `DJANGO_DB_HOST`, `DJANGO_DB_PORT`
- `DJANGO_USE_SQLITE_FOR_TESTS` (padrao: `True`)
- `CORS_ALLOWED_ORIGINS`
- `APP_ENV` (`dev`/`prod`)
- `SMTP_*` (quando `APP_ENV=prod`)
- `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` (relatorio AI semanal)

Rotas principais (`/api/v1/`)
-----------------------------

Autenticacao (`accounts`)
-------------------------
- `POST /auth/register/`
- `POST /auth/verify-email/`
- `POST /auth/login/`
- `POST /auth/refresh/`
- `GET /auth/me/`
- `PUT/PATCH /auth/update-profile/`
- `POST /auth/change-password/`

Goal calendars e weekly activities (`goal_calendars`)
-----------------------------------------------------
- `GET/POST /goal-calendars/`
- `GET/PUT/DELETE /goal-calendars/<uuid:pk>/`
- `GET /goal-calendars/<uuid:goal_calendar_id>/weeks/`
- `GET /goal-calendars/activities/metric-types/`
- `GET/POST /goal-calendars/weeks/<uuid:week_id>/activities/`
- `GET/PUT /goal-calendars/weeks/<uuid:week_id>/activities/<uuid:pk>/`
- `POST /goal-calendars/weeks/<uuid:week_id>/activities/<uuid:pk>/progress/frequency/`
- `POST /goal-calendars/weeks/<uuid:week_id>/activities/<uuid:pk>/progress/quantity/`
- `POST /goal-calendars/weeks/<uuid:week_id>/activities/<uuid:pk>/progress/specific-days/`
- `GET /goal-calendars/weeks/<uuid:week_id>/activities/report/`
- `POST /goal-calendars/weeks/<uuid:week_id>/activities/report/ai/`

Objectives (`objectives`)
-------------------------
- `POST /objectives/`
- `GET /objectives/types/`
- `GET /objectives/type/<str:objective_type>/`
- `GET /objectives/goal-calendar/<uuid:goal_calendar_id>/`
- `GET/PUT/DELETE /objectives/<uuid:pk>/`
- `POST /objectives/<uuid:pk>/complete/`

Wallets (`wallets`)
-------------------
- Carteiras:
  - `GET/POST /wallets/`
  - `GET/PUT/PATCH/DELETE /wallets/<uuid:pk>/`
  - Campos calculados na leitura: `remaining_total_limit`, `remaining_cycle_limit`
- Categorias:
  - `GET/POST /wallets/categories/`
  - `GET/PUT/PATCH/DELETE /wallets/categories/<uuid:pk>/`
- Ciclos:
  - `POST /wallets/cycle/resolve/` (por `date` ou `month`)
  - `GET /wallets/cycle/?wallet=<wallet_id>`
  - `GET /wallets/cycle/<uuid:pk>/`
  - `GET /wallets/cycle/<uuid:pk>/billing-summary/`
  - `PUT/PATCH /wallets/cycle/<uuid:pk>/` (somente `limit`)
- Despesas:
  - `GET/POST /wallets/expenses/?expense_cycle=<cycle_id>`
  - `PATCH /wallets/expenses/<uuid:pk>/` (somente despesas `single_expense`)
  - `POST /wallets/expenses/<uuid:pk>/cancel-recurring/`
- Parcelamentos:
  - `POST /wallets/installment-series/`
  - `PUT /wallets/installment-series/<uuid:pk>/`
  - `DELETE /wallets/installment-series/<uuid:pk>/`

Observacoes de negocio (wallets)
--------------------------------
- Ciclos podem cruzar mes (`cycle_starts` diferente de `cycle_ends`).
- `remaining_total_limit` considera limite total da carteira menos:
  - total gasto no ciclo atual
  - gastos de ciclos futuros apenas de `single_expense` e `installment_expense`
- `remaining_cycle_limit` considera limite do ciclo atual menos total gasto do ciclo atual.
- `billing-summary` inclui:
  - total do ciclo
  - total por categoria
  - total de parcelamento do ciclo
  - total de recorrencia do ciclo
  - total de parcelamento futuro
  - `remaining_limit_per_day` somente quando a data atual estiver entre `start_date` e `end_date` do ciclo.

Colecoes de teste
-----------------
- Requests HTTP de exemplo em `api-test/`:
  - `wallets.http`
  - `wallet-cycles.http`
  - `wallet-expenses.http`
  - `wallet-categories.http`
  - `wallet-installment-series.http`

Testes
------
- Suite completa: `python manage.py test`
- Modulo wallets: `python manage.py test wallets.tests`
