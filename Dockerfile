FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock /app/
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv venv --seed /app/.venv \
    && uv sync --frozen --no-install-project

COPY . /app

ENV PATH="/app/.venv/bin:$PATH"

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
