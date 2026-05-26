# project_service

Проекты, посты, задачи, участники. Публикует события task/post в Kafka, слушает profile и ответы.

## Порт и health

Внутри Docker: **8000**. HTTP API через роутер проектов.

```bash
curl http://localhost:8000/health
```

## Kafka

| Направление | Топик |
|-------------|--------|
| In | `profile_service.user.registered`, `profile_service.profile.changed`, `profile_service.user.deleted` |
| In | `project-answers` (`answer.created`, `answer.deleted`) |
| Out | `project_service.task.created` / `.changed` / `.delete` |
| Out | `project_service.post.created` / `.changed` / `.delete` |

Константы: `src/kafka_topics.py`.

## База данных

- БД: `project_db`
- Миграции: `migrations/` (yoyo)
- Таблицы: `project`, `post`, `task`, `denorm_user`, `project_user_connection`, `tags`, …

Миграция `0008` — удаление устаревшей колонки `avatar_url` из `denorm_user`.

## API

REST под префиксом роутера (см. `src/api/http/project_router.py`).  
В ответах по задачам/постам — **`creator_name`** из `denorm_user`.

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `LOG_LEVEL` | Уровень loguru (`INFO`) |
| `DATABASE_DSN` | PostgreSQL |
| `KAFKA_BOOTSTRAP` | Kafka |
| `KAFKA_TOPIC_ANSWERS` | `project-answers` |
| `HTTP_HOST` / `HTTP_PORT` | HTTP-сервер |

## Логи

Используется **loguru** (цветной вывод в stderr).

Формат:

```
2026-05-25 12:00:00 | INFO     | src.main:36 - Postgres connected
```

Настройка: `_setup_logger()` в `src/main.py` (команда `run`).

**Docker:**

```bash
docker logs project -f
```

**Типичные сообщения:**

- `Postgres connected` / `connection failed`
- `Kafka producer started`
- `Profile Kafka consumer created`
- `Dispatching topic=…` (consumers)
- `Sent event to project_service.task.created`

```bash
docker logs project 2>&1 | grep -E "ERROR|Kafka|consumer"
```

## CLI

```bash
# HTTP + consumers
python -m src.main run

# миграции
python -m src.main migrate
python -m src.main migrate-down
```

## Запуск

```bash
cd ../infra_faberge && make project-dev
```

## Тесты

```bash
uv run pytest tests/unit -q          # только unit
uv run pytest -q                     # unit + integration
```
