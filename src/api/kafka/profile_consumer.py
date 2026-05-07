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
            logger.debug(f"ProfileKafkaConsumer received message: {message.value}")
            event = json.loads(message.value.decode('utf-8'))
            event_type = event.get("event_type")
            event_data = event.get("data", {})
            user_id = event_data.get("user_id")
            
            logger.info(f"Processing Kafka event - type: {event_type}, user_id: {user_id}, event_data keys: {list(event_data.keys())}")

            if not user_id:
                logger.warning("Missing user_id in event")
                return

            update_data = {}

            if event_type == "user.created":
                name = event_data.get("first_name", "")
                if name:
                    update_data["name"] = name
                else:
                    update_data["name"] = "Unknown"

            elif event_type == "user.profile.updated":
                if "name" in event_data:
                    update_data["name"] = event_data["name"]
                else:
                    logger.debug(f"No name in profile update event: {event}")
                    return

            elif event_type == "user.avatar.updated":
                if "avatar_link" in event_data:
                    update_data["avatar_url"] = event_data["avatar_link"]
                else:
                    logger.debug(
                        f"No avatar_link in avatar update event: {event}")
                    return

            logger.info(f"Calling upsert_denorm_user - user_id: {user_id}, data: {update_data}")
            await self._project_service.upsert_denorm_user(
                user_id=UUID(user_id),
                data=update_data
            )
            logger.info(
                f"Successfully processed {event_type} event for user {user_id} with data: {update_data}")

        except Exception as e:
            logger.error(
                f"Error processing profile event: {e}, message: {message.value}")
