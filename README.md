Yearly Goal Slice API
=====================

API em Django para cadastro de usuarios, calendarios de metas semanais e objetivos vinculados ou nao a esses calendarios. Inclui autenticacao via JWT e documentacao Swagger/Redoc.

Como rodar localmente
---------------------
- Instale o `uv` (via `pip`): `pip install uv`
- Crie o ambiente virtual: `uv venv .venv`
- Ative: `source .venv/bin/activate`
- Instale dependencias: `uv sync`
- Aplique migracoes (cria o banco SQLite em `db.sqlite3`): `python manage.py migrate`
- Crie um superuser (opcional, para admin): `python manage.py createsuperuser`
- Suba o servidor: `python manage.py runserver`
- Documentacao interativa: `http://localhost:8000/swagger/` ou `http://localhost:8000/redoc/`

Principais dependencias
-----------------------
- Django 4.2.16
- Django REST Framework
- djangorestframework-simplejwt (JWT)
- drf-yasg (Swagger/Redoc)

Modulos e responsabilidades
---------------------------
- accounts: modelo de usuario com UUID como chave primaria; endpoints de registro, login/refresh via JWT e consulta do usuario autenticado.
- goal_calendars: calendarios semanais de metas por usuario; calcula data final; soft-delete via `active`; inclui weekly activities com tres metricas (frequencia, quantidade ou dias especificos), progresso por metrica e relatorio semanal agregado.
- objectives: objetivos de longo/medio prazo ou atrelados a um calendario; validacoes para evitar duplicidades ativas e garantir vinculo correto com calendarios do proprio usuario; soft-delete e marca de conclusao.

Rotas principais (prefixo `/api/v1/`)
-------------------------------------
- Autenticacao
  - `POST /auth/register/` cria usuario (username, email, senha, nome, sobrenome).
  - `POST /auth/login/` retorna `access` e `refresh`.
  - `POST /auth/refresh/` renova token.
  - `GET /auth/me/` dados do usuario autenticado.
  - `PUT /auth/update-profile/` atualiza perfil do usuario autenticado.
  - `PUT /auth/change-password/` altera senha do usuario autenticado.
- Goal calendars
  - `GET/POST /goal-calendars/` lista/cria calendarios do usuario logado.
  - `GET/PUT/DELETE /goal-calendars/<uuid>/` recupera, atualiza ou inativa (soft-delete) um calendario do usuario.
- Weekly activities (metas semanais dentro de um calendario)
  - `GET/POST /goal-calendars/<goal_calendar_id>/activities/?week_number=N` lista/cria atividades da semana N.
  - `GET/PUT/PATCH /goal-calendars/<goal_calendar_id>/activities/<uuid>/` consulta/edita atividade.
  - `POST /goal-calendars/<goal_calendar_id>/activities/<uuid>/progress/frequency/` incrementa progresso de frequencia (`day`).
  - `POST /goal-calendars/<goal_calendar_id>/activities/<uuid>/progress/quantity/` soma progresso de quantidade (`amount`).
  - `POST /goal-calendars/<goal_calendar_id>/activities/<uuid>/progress/specific-days/` marca dia concluido para metricas de dias especificos (`day`).
  - `GET /goal-calendars/<goal_calendar_id>/activities/report/?week_number=N` relatorio percentual por atividade e media geral da semana.
- Objectives
  - `POST /objectives/` cria objetivo para o usuario logado.
  - `GET /objectives/type/<objective_type>/` lista objetivos ativos filtrados por tipo (`LONG_TERM`, `MEDIUM_TERM`, `GOAL_CALENDAR`).
  - `GET /objectives/goal-calendar/<uuid>/` lista objetivos vinculados a um calendario ativo do usuario.
  - `GET/PUT/DELETE /objectives/<uuid>/` recupera/edita/inativa objetivo.
  - `POST /objectives/<uuid>/complete/` marca objetivo como concluido.

Configuracoes e comportamento
-----------------------------
- Banco: SQLite (arquivo `db.sqlite3`).
- Auth: `rest_framework_simplejwt.authentication.JWTAuthentication`; permissoes padrao exigem usuario autenticado.
- Internacionalizacao: `TIME_ZONE=America/Sao_Paulo`, `USE_TZ=True`.
- Admin: painel nativo em `/admin/`.

Testes
------
Rodar testes unitarios: `python manage.py test`
