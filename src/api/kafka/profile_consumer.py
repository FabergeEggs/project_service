import json
import asyncio
from uuid import UUID
from aiokafka import AIOKafkaConsumer
from src.services.project_service import ProjectService
from src.api.kafka.base_consumer import BaseKafkaConsumer
from loguru import logger
from src.models.project import DenormUser, ProjectRoleEnum


class ProfileKafkaConsumer(BaseKafkaConsumer):
    def __init__(
        self, consumer: AIOKafkaConsumer, project_service: ProjectService
    ) -> None:
        super().__init__(consumer)
        self._project_service = project_service

    async def _handle_message(self, message):
        try:
            event = json.loads(message.value.decode('utf-8'))
            event_type = event.get("event_type")
            user_id = event.get("user_id")

            if not user_id:
                logger.warning("Missing user_id")
                return

            fields = {}
            if event_type in ("user.created", "user.profile.updated"):
                if "name" in event:
                    fields["name"] = event["name"]
            elif event_type == "user.avatar.updated":
                if "avatar_link" in event:
                    fields["avatar_url"] = event["avatar_link"]

            if not fields:
                logger.debug(f"No fields to update in event: {event}")
                return

            await self._project_service.upsert_denorm_user(
                user_id=UUID(user_id),
                fields=fields,
                defaults={"role": ProjectRoleEnum.VOLUNTEER}
            )

        except Exception as e:
            logger.error(
                f"Error processing profile event: {e}, message: {message.value}")
