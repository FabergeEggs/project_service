import asyncio

import typer
from psycopg_pool import AsyncConnectionPool
import uvicorn
import sys
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI
from loguru import logger
from src.api.http.project_router import create_project_router
from src.adapters.clients.kafka_producer import KafkaProducerClient
from src.adapters.repository.postgres.project_repository import ProjectPostgresRepository
from src.api.kafka.answer_consumer import AnswerKafkaConsumer
from src.api.kafka.comments_consumer import CommentsKafkaConsumer
from src.api.kafka.profile_consumer import ProfileKafkaConsumer
from src.services.project_service import ProjectService
from src.config import Settings

from migrations.migrate import up, down, drop


async def _run(settings: Settings) -> None:
    # Connecting database interconnection implementation with Duck Typing
    logger.debug("Connecting to database: {}", settings.database_dsn)

    pool = AsyncConnectionPool(
        conninfo=settings.database_dsn,
        min_size=settings.database_min_connections,
        max_size=settings.database_max_connections,
    )

    try:
        async with pool.connection() as conn:
            logger.info("Postgres connected")
    except Exception as e:
        logger.error("Postgres connection failed: {}", e)

    project_repository = ProjectPostgresRepository(pool)
    logger.debug("Database connection established")

    # Starting Kafka producer
    logger.debug("Starting Kafka producer: {}", settings.kafka_bootstrap)
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap)
    await producer.start()
    kafka_producer = KafkaProducerClient(producer)
    logger.debug("Kafka producer started")

    # Starting service itself with prepared submodules
    project_service = ProjectService(
        project_repository, kafka_producer)
    logger.debug("Project Service started")

    # Start Fastapi app and make it able to use all endpoints
    fastapi_app = FastAPI(title="Project Service")
    router = create_project_router(project_service)
    fastapi_app.include_router(router)
    logger.debug("HTTP router registered")

    # Create kafka consumers to receive messages from other services
    # Answers consumer
    answer_consumer = AIOKafkaConsumer(
        settings.kafka_topic_answers,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=f"{settings.kafka_group_id}-answer",
    )
    answer_kafka_consumer = AnswerKafkaConsumer(
        answer_consumer, project_service)
    logger.debug(
        "Answer Kafka consumer created: topic={}, group={}",
        settings.kafka_topic_answers,
        settings.kafka_group_id,
    )

    # Comments consumer
    comment_consumer = AIOKafkaConsumer(
        settings.kafka_topic_comments,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=f"{settings.kafka_group_id}-comment",
    )
    comment_kafka_consumer = AnswerKafkaConsumer(
        comment_consumer, project_service)
    logger.debug(
        "Answer Kafka consumer created: topic={}, group={}",
        settings.kafka_topic_comments,
        settings.kafka_group_id,
    )

    # Profiles consumer
    profile_consumer = AIOKafkaConsumer(
        settings.kafka_topic_profile,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=f"{settings.kafka_group_id}-profile",
    )
    profile_kafka_consumer = ProfileKafkaConsumer(
        profile_consumer, project_service)
    logger.debug(
        "Profile Kafka consumer created: topic={}, group={}",
        settings.kafka_topic_profile,
        settings.kafka_group_id,
    )

    # Starting service of assembled app with prepared parameters using uvicorn
    config = uvicorn.Config(
        fastapi_app,
        host=settings.http_host,
        port=settings.http_port
    )
    server = uvicorn.Server(config)
    logger.info("Starting service on {}:{}",
                settings.http_host, settings.http_port)

    try:
        await asyncio.gather(
            server.serve(),
            answer_kafka_consumer.start(),
            comment_kafka_consumer.start(),
            profile_kafka_consumer.start(),
        )
    finally:
        logger.debug("Shutting down")
        await producer.stop()
        await pool.close()
        logger.info("Shutdown complete")


app = typer.Typer()


def _setup_logger(settings: Settings) -> None:
    logger.remove()
    logger.add(
        sink=sys.stderr,
        level=settings.log_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - {message}",
    )


@app.command()
def run() -> None:
    settings = Settings()
    _setup_logger(settings)
    logger.debug("Settings loaded: {}", settings.model_dump())
    asyncio.run(_run(settings))


@app.command()
def migrate() -> None:
    settings = Settings()
    _setup_logger(settings)
    logger.info("Running migration...")
    up(settings.database_dsn)
    logger.info("Migration completed.")


@app.command()
def migrate_down() -> None:
    settings = Settings()
    _setup_logger(settings)
    logger.info("Rolling back migration...")
    down(settings.database_dsn)
    logger.info("Rollback completed.")


@app.command()
def migrate_drop() -> None:
    settings = Settings()
    _setup_logger(settings)
    logger.info("Dropping database...")
    drop(settings.database_dsn)
    logger.info("Database dropped.")


if __name__ == "__main__":
    app()
