import json
from uuid import UUID
from aiokafka import AIOKafkaConsumer
from src.services.project_service import ProjectService
from src.api.kafka.base_consumer import BaseKafkaConsumer
from loguru import logger


class ProfileKafkaConsumer(BaseKafkaConsumer):
    """
    Consumer for user profile events from the user service.

    Listens for user creation, profile updates, and avatar update events
    to keep denormalized user data synchronized in the project database.
    This enables efficient queries without joining to an external service.
    """

    def __init__(
        self, consumer: AIOKafkaConsumer, project_service: ProjectService
    ) -> None:
        """
        Initialize the profile Kafka consumer.

        Args:
            consumer: Configured AIOKafkaConsumer instance.
            project_service: Service instance for upserting denormalized user data.
        """
        super().__init__(consumer)
        self._project_service = project_service

    async def _handle_message(self, message):
        """
        Process a user profile event from Kafka.

        Handles three event types:
        - user.created: Creates a new denormalized user record
        - user.profile.updated: Updates user name
        - user.avatar.updated: Updates user avatar URL

        Expected event structure:
        {
            "event_type": "user.created" | "user.profile.updated" | "user.avatar.updated",
            "data": {
                "user_id": "uuid-string",
                "first_name": "name",  # for user.created
                "name": "full name",    # for user.profile.updated
                "avatar_link": "url"    # for user.avatar.updated
            }
        }

        Args:
            message: Raw Kafka message containing the profile event.
        """
        try:
            logger.debug(
                f"ProfileKafkaConsumer received message: {message.value}")
            event = json.loads(message.value.decode('utf-8'))
            event_type = event.get("event_type")
            event_data = event.get("data", {})
            user_id = event_data.get("user_id")

            logger.info(
                f"Processing Kafka event - type: {event_type}, user_id: {user_id}, event_data keys: {list(event_data.keys())}")

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

            logger.info(
                f"Calling upsert_denorm_user - user_id: {user_id}, data: {update_data}")
            await self._project_service.upsert_denorm_user(
                user_id=UUID(user_id),
                data=update_data
            )
            logger.info(
                f"Successfully processed {event_type} event for user {user_id} with data: {update_data}")

        except Exception as e:
            logger.error(
                f"Error processing profile event: {e}, message: {message.value}")
