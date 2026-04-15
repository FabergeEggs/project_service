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
from src.api.kafka.project_consumer import ProjectKafkaConsumer
from src.services.project_service import ProjectService
from src.config import Settings


async def _run(settings: Settings) -> None:
    # Connecting database interconnection implementation with Duck Typing
    logger.debug("Connecting to database: {}", settings.database_dsn)

    pool = AsyncConnectionPool(
        conninfo=settings.database_dsn,
        min_size=settings.database_min_connections,
        max_size=settings.database_max_connections,
    )

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

    # Create kafka consumer to receive messages from other services
    consumer = AIOKafkaConsumer(
        settings.kafka_topic_commands,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id=settings.kafka_group_id,
    )
    kafka_consumer = ProjectKafkaConsumer(consumer, project_service)
    logger.debug(
        "Kafka consumer created: topic={}, group={}",
        settings.kafka_topic_commands,
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
        await asyncio.gather(server.serve(), kafka_consumer.start())
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


if __name__ == "__main__":
    app()
