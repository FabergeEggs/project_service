import json
from uuid import UUID
from aiokafka import AIOKafkaConsumer
from src.services.project_service import ProjectService
from src.api.kafka.base_consumer import BaseKafkaConsumer
from loguru import logger


class CommentsKafkaConsumer(BaseKafkaConsumer):
    """
    Consumer for comment events from the comment service.

    Listens for comment creation and deletion events and updates the
    corresponding post's comment count in the project service.
    """

    def __init__(self, consumer: AIOKafkaConsumer, project_service: ProjectService) -> None:
        """
        Initialize the comments Kafka consumer.

        Args:
            consumer: Configured AIOKafkaConsumer instance.
            project_service: Service instance for updating post comment counts.
        """
        super().__init__(consumer)
        self._project_service = project_service

    async def _handle_message(self, message):
        """
        Process a comment event from Kafka.

        Expects events with structure:
        {
            "type": "comment.created" or "comment.deleted",
            "post_id": "uuid-string"
        }

        Args:
            message: Raw Kafka message containing the comment event.
        """
        try:
            event = json.loads(message.value.decode('utf-8'))
            event_type = event.get("type")
            post_id_str = event.get("post_id")

            if not post_id_str:
                logger.warning(f"Missing post_id in event: {event}")
                return

            post_id = UUID(post_id_str)

            if event_type == "comment.created":
                await self._project_service.increment_post_answer(post_id)
            elif event_type == "comment.deleted":
                await self._project_service.decrement_post_answer(post_id)
            else:
                logger.debug(f"Ignoring event type: {event_type}")
        except Exception as e:
            logger.error(
                f"Error processing comments event: {e}, message: {message.value}")
