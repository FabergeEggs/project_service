import json
import asyncio
from uuid import UUID
from aiokafka import AIOKafkaConsumer
from src.services.project_service import ProjectService
from src.api.kafka.base_consumer import BaseKafkaConsumer
from loguru import logger


class ProfileKafkaConsumer(BaseKafkaConsumer):
    def __init__(
        self, consumer: AIOKafkaConsumer, project_service: ProjectService
    ) -> None:
        super().__init__(consumer)
        self._project_service = project_service

    async def _handle_message(self, message):
        try:
            event = json.loads(message.value.decode('utf-8'))
            user_id = self._safe_get(event, "user_id", "id")
            name = self._safe_get(event, "name", "username")
            avatar_link = self._safe_get(event, "avatar_link", "avatar")

            if not user_id or not name:
                logger.warning(f"Invalid user event, missing fields: {event}")
                return

            await self._project_service.upsert_denorm_user(
                user_id=UUID(user_id),
                name=name,
                avatar_link=avatar_link or ""
            )

            logger.debug(f"Upserted denorm user: {user_id} ({name})")

        except Exception as e:
            logger.error(
                f"Error processing profile event: {e}, message: {message.value}")
