FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock* ./
COPY migrations ./migrations
COPY src ./src

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN uv sync --frozen --no-dev

COPY . .

CMD ["uv", "run", "-m", "src.main", "run"]