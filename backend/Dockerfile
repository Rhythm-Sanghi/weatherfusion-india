FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
COPY docker/backend-entrypoint.sh /usr/local/bin/backend-entrypoint

RUN pip install --no-cache-dir . \
    && chmod +x /usr/local/bin/backend-entrypoint

EXPOSE 8000

CMD ["/usr/local/bin/backend-entrypoint"]
