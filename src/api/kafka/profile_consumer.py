import json
from uuid import UUID

from aiokafka import AIOKafkaConsumer

from src import kafka_topics as topics
from src.api.kafka.base_consumer import BaseKafkaConsumer
from src.models.project import ProjectRoleEnum
from src.services.project_service import ProjectService
from loguru import logger


class ProfileKafkaConsumer(BaseKafkaConsumer):
    def __init__(
        self, consumer: AIOKafkaConsumer, project_service: ProjectService
    ) -> None:
        super().__init__(consumer)
        self._project_service = project_service

    async def _handle_message(self, message):
        try:
            event = json.loads(message.value.decode("utf-8"))
            event_type = event.get("event_type")
            user_id_raw = event.get("user_id")
            if not user_id_raw:
                nested = event.get("data")
                if isinstance(nested, dict):
                    user_id_raw = nested.get("user_id")

            if not user_id_raw:
                logger.warning("Missing user_id in profile event: %s", event)
                return

            user_id = UUID(str(user_id_raw))
            fields: dict = {}
            defaults = {"role": ProjectRoleEnum.VOLUNTEER}

            if event_type == topics.PROFILE_USER_REGISTERED:
                nested = event.get("data")
                if isinstance(nested, dict):
                    first = nested.get("first_name") or event.get("first_name") or ""
                    last = nested.get("last_name") or event.get("last_name") or ""
                else:
                    first = event.get("first_name") or ""
                    last = event.get("last_name") or ""
                name = f"{first} {last}".strip()
                if name:
                    fields["name"] = name

            elif event_type == topics.PROFILE_CHANGED:
                changes = event.get("changes", {})
                if not isinstance(changes, dict):
                    nested = event.get("data")
                    if isinstance(nested, dict):
                        changes = nested.get("changes", {})
                if isinstance(changes, dict) and changes.get("name"):
                    fields["name"] = changes["name"]

            elif event_type == topics.PROFILE_USER_DELETED:
                defaults = {"role": ProjectRoleEnum.DELETED}
                fields["name"] = fields.get("name", "")

            else:
                logger.debug("Ignoring unknown profile event type: %s", event_type)
                return

            if not fields and event_type != topics.PROFILE_USER_DELETED:
                logger.debug("No denorm fields to update in event: %s", event)
                return

            await self._project_service.upsert_denorm_user(
                user_id=user_id,
                fields=fields,
                defaults=defaults,
            )

        except Exception as e:
            logger.error(
                f"Error processing profile event: {e}, message: {message.value}"
            )
