from uuid import UUID
from aiokafka import AIOKafkaProducer
from src.models.project import Project, Post, Task
import json
from datetime import datetime, timezone
from loguru import logger


class KafkaProducerClient:
    """Client for producing Kafka events for project, post, and task operations."""

    def __init__(self, producer: AIOKafkaProducer) -> None:
        """
        Initialize the Kafka producer client.

        Args:
            producer: AIOKafkaProducer instance for sending messages to Kafka topics.
        """
        self._producer = producer

    async def _send_event(self, topic: str, key: str, value: dict) -> None:
        """
        Internal method to send an event to a Kafka topic.

        Args:
            topic: Kafka topic name to send the event to.
            key: Message key used for partitioning.
            value: Dictionary containing the event data to be serialized as JSON.

        Raises:
            Exception: If sending the event fails, the exception is logged and re-raised.
        """
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

    async def send_create_project(self, project: Project, creator_name: str = "") -> None:
        """
        Send a project.created event when a new project is created.

        Args:
            project: Project object containing the project details.
            creator_name: Display name of the creator (username).
        """
        await self._send_event(
            topic="project.created",
            key=str(project.id),
            value={
                "type": "project.created",
                "project_id": str(project.id),
                "label": project.label,
                "creator_id": str(project.creator_id),
                "creator_name": creator_name,
                "status": project.status.value,
                "created_at": project.created_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_update_project(self, project: Project, creator_name: str = "") -> None:
        """
        Send a project.updated event when a project is modified.

        Args:
            project: Project object containing the updated project details.
            creator_name: Display name of the creator (username).
        """
        await self._send_event(
            topic="project.updated",
            key=str(project.id),
            value={
                "type": "project.updated",
                "project_id": str(project.id),
                "label": project.label,
                "creator_id": str(project.creator_id),
                "creator_name": creator_name,
                "status": project.status.value,
                "updated_at": project.updated_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_create_post(self, post: Post, creator_name: str = "") -> None:
        """
        Send a post.created event when a new post is created.

        Args:
            post: Post object containing the post details.
            creator_name: Display name of the creator (username).
        """
        await self._send_event(
            topic="post.created",
            key=str(post.post_id),
            value={
                "type": "post.created",
                "post_id": str(post.post_id),
                "project_id": str(post.project_id),
                "creator_id": str(post.creator_id),
                "creator_name": creator_name,
                "label": post.label,
                "short_description": post.short_description,
                "media_ids": [str(m) for m in (post.media_ids or [])],
                "created_at": post.created_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_update_post(self, post: Post, creator_name: str = "") -> None:
        """
        Send a post.updated event when a post is modified.

        Args:
            post: Post object containing the updated post details.
            creator_name: Display name of the creator (username).
        """
        await self._send_event(
            topic="post.updated",
            key=str(post.post_id),
            value={
                "type": "post.updated",
                "post_id": str(post.post_id),
                "project_id": str(post.project_id),
                "creator_id": str(post.creator_id),
                "creator_name": creator_name,
                "label": post.label,
                "short_description": post.short_description,
                "media_ids": [str(m) for m in (post.media_ids or [])],
                "updated_at": post.updated_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_delete_post(self, post_id: UUID) -> None:
        """
        Send a post.deleted event when a post is deleted.

        Args:
            post_id: UUID of the post being deleted.
        """
        await self._send_event(
            topic="post.deleted",
            key=str(post_id),
            value={
                "type": "post.deleted",
                "post_id": str(post_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_create_task(self, task: Task, creator_name: str = "") -> None:
        """
        Send a task.created event when a new task is created.

        Args:
            task: Task object containing the task details.
            creator_name: Display name of the creator (username).
        """
        await self._send_event(
            topic="task.created",
            key=str(task.task_id),
            value={
                "type": "task.created",
                "task_id": str(task.task_id),
                "project_id": str(task.project_id),
                "creator_id": str(task.creator_id),
                "creator_name": creator_name,
                "label": task.label,
                "short_description": task.short_description,
                "status": task.status.value,
                "answer_count": task.answers_count,
                "media_ids": [str(m) for m in (task.media_ids or [])],
                "created_at": task.created_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_update_task(self, task: Task, creator_name: str = "") -> None:
        """
        Send a task.updated event when a task is modified.

        Args:
            task: Task object containing the updated task details.
            creator_name: Display name of the creator (username).
        """
        await self._send_event(
            topic="task.updated",
            key=str(task.task_id),
            value={
                "type": "task.updated",
                "task_id": str(task.task_id),
                "project_id": str(task.project_id),
                "creator_id": str(task.creator_id),
                "creator_name": creator_name,
                "label": task.label,
                "short_description": task.short_description,
                "status": task.status.value,
                "answer_count": task.answers_count,
                "media_ids": [str(m) for m in (task.media_ids or [])],
                "updated_at": task.updated_at.isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def send_delete_task(self, task_id: UUID) -> None:
        """
        Send a task.deleted event when a task is deleted.

        Args:
            task_id: UUID of the task being deleted.
        """
        await self._send_event(
            topic="task.deleted",
            key=str(task_id),
            value={
                "type": "task.deleted",
                "task_id": str(task_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
