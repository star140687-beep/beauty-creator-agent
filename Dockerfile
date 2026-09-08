FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY config ./config
COPY data/samples ./data/samples
COPY data/openbeautyfacts ./data/openbeautyfacts
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn beauty_creator_agent.main:app --host 0.0.0.0 --port 8000"]
