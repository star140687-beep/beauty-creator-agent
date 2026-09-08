FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY frontend ./frontend
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
EXPOSE 8501
CMD ["streamlit", "run", "frontend/app.py", "--server.address=0.0.0.0"]

