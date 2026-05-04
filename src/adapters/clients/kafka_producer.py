from uuid import UUID
from aiokafka import AIOKafkaProducer
from src.models.project import Project, Post, Task
import json
from datetime import datetime, timezone
from loguru import logger


class KafkaProducerClient:
    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

    async def _send_event(self, topic: str, key: str, value: dict) -> None:
        try:
            await self._producer.send(
                topic=topic,
                key=key.encode('utf-8'),
                value=json.dumps(value, default=str).encode('utf-8')
            )
            logger.debug(f"Sent event to {topic}: {value}")
        except Exception as e:
            logger.error(f"Failed to send event to {topic}: {e}")
            raise

    async def send_create_project(self, project: Project) -> None:
        await self._send_event(
            topic="project.created",
            key=str(project.id),
            value={
                "type": "project.created",
                "project_id": str(project.id),
                "label": project.label,
                "creator_id": str(project.creator_id),
                "status": project.status.value,
                "created_at": project.created_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_update_project(self, project: Project) -> None:
        await self._send_event(
            topic="project.updated",
            key=str(project.id),
            value={
                "type": "project.updated",
                "project_id": str(project.id),
                "label": project.label,
                "creator_id": str(project.creator_id),
                "status": project.status.value,
                "updated_at": project.updated_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_create_post(self, post: Post) -> None:
        await self._send_event(
            topic="post.created",
            key=str(post.post_id),
            value={
                "type": "post.created",
                "post_id": str(post.post_id),
                "project_id": str(post.project_id),
                "creator_id": str(post.creator_id),
                "label": post.label,
                "short_description": post.short_description,
                "created_at": post.created_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_update_post(self, post: Post) -> None:
        await self._send_event(
            topic="post.updated",
            key=str(post.post_id),
            value={
                "type": "post.updated",
                "post_id": str(post.post_id),
                "project_id": str(post.project_id),
                "creator_id": str(post.creator_id),
                "label": post.label,
                "short_description": post.short_description,
                "updated_at": post.updated_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_delete_post(self, post_id: UUID) -> None:
        await self._send_event(
            topic="post.deleted",
            key=str(post_id),
            value={
                "type": "post.deleted",
                "post_id": str(post_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_create_task(self, task: Task) -> None:
        await self._send_event(
            topic="task.created",
            key=str(task.task_id),
            value={
                "type": "task.created",
                "task_id": str(task.task_id),
                "project_id": str(task.project_id),
                "creator_id": str(task.creator_id),
                "label": task.label,
                "short_description": task.short_description,
                "status": task.status.value,
                "answer_count": task.answers_count,
                "created_at": task.created_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_update_task(self, task: Task) -> None:
        await self._send_event(
            topic="task.updated",
            key=str(task.task_id),
            value={
                "type": "task.updated",
                "task_id": str(task.task_id),
                "project_id": str(task.project_id),
                "creator_id": str(task.creator_id),
                "label": task.label,
                "short_description": task.short_description,
                "status": task.status.value,
                "answer_count": task.answers_count,
                "updated_at": task.updated_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_delete_task(self, task_id: UUID) -> None:
        await self._send_event(
            topic="task.deleted",
            key=str(task_id),
            value={
                "type": "task.deleted",
                "task_id": str(task_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
