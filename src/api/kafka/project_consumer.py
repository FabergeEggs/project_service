import json
import asyncio
from uuid import UUID
from aiokafka import AIOKafkaConsumer
from src.services.project_service import ProjectService
from loguru import logger


class ProjectKafkaConsumer:
    def __init__(
        self, consumer: AIOKafkaConsumer, project_service: ProjectService
    ) -> None:
        self._consumer = consumer
        self._project_service = project_service

    async def start(self) -> None:
        await self._consumer.start()
        logger.info("Kafka consumer started")
        try:
            async for message in self._consumer:
                await self._handle_message(message)
        except asyncio.CancelledError:
            logger.info("Answers Kafka consumer stopped")
        finally:
            await self._consumer.stop()

    async def _handle_message(self, message):
        try:
            event = json.loads(message.value.decode('utf-8'))
            event_type = event.get("type")
            task_id_str = event.get("task_id")

            if not task_id_str:
                logger.warning(f"Missing task_id in event: {event}")
                return

            task_id = UUID(task_id_str)

            if event_type == "answer.created":
                await self._project_service.increment_task_answers(task_id)
            elif event_type == "answer.deleted":
                await self._project_service.decrement_task_answer(task_id)
            else:
                logger.debug(f"Ignoring event type: {event_type}")
        except Exception as e:
            logger.error(
                f"Error processing answers event: {e}, message: {message.value}")
