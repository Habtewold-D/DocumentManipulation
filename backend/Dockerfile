FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
RUN python - <<'PY'
import tomllib
import subprocess

with open('pyproject.toml', 'rb') as handle:
    pyproject = tomllib.load(handle)

deps = pyproject.get('project', {}).get('dependencies', [])
if deps:
    subprocess.check_call(['pip', 'install', '--no-cache-dir', *deps])
PY

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

EXPOSE 8000
