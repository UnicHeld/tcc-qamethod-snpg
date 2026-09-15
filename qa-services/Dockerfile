FROM python:3.12.14-slim-bookworm AS dependencies

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system --gid 10001 qa-method \
    && useradd --system --uid 10001 --gid qa-method --home-dir /app qa-method

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --requirement requirements.txt


FROM dependencies AS runtime

COPY --chown=qa-method:qa-method app ./app

USER qa-method

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM dependencies AS development

COPY requirements-dev.txt pyproject.toml ./
RUN python -m pip install --no-cache-dir --requirement requirements-dev.txt

COPY --chown=qa-method:qa-method app ./app

USER qa-method

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


FROM development AS test

COPY --chown=qa-method:qa-method tests ./tests

CMD ["sh", "-c", "ruff check --no-cache app tests && pytest -p no:cacheprovider -m 'not live'"]
