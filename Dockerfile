FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc=4:14.2.0-1 \
    libpq-dev=17.10-0+deb13u1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock* ./
COPY migrations ./migrations
COPY src ./src

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN uv sync --frozen --no-dev

COPY . .

CMD ["uv", "run", "-m", "src.main", "run"]
