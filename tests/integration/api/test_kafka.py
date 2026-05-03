import json
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock

from src.api.kafka.answer_consumer import AnswerKafkaConsumer


@pytest.fixture
def consumer():
    return AsyncMock()


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def kafka():
    return AsyncMock()


@pytest.fixture
def project_service(repo, kafka):
    from src.services.project_service import ProjectService
    return ProjectService(
        project_repository=repo,
        kafka_producer=kafka
    )


@pytest.fixture
def answers_consumer(consumer, project_service):
    return AnswerKafkaConsumer(consumer, project_service)  # ← правильное имя


@pytest.mark.asyncio
class TestAnswerKafkaConsumer:
    async def test_handle_answer_created(self, answers_consumer, project_service):
        task_id = uuid4()
        message = AsyncMock()
        message.value = json.dumps({
            "type": "answer.created",
            "task_id": str(task_id)
        }).encode('utf-8')

        await answers_consumer._handle_message(message)

        # Проверяем, что метод сервиса был вызван
        project_service.increment_task_answer.assert_awaited_once_with(task_id)

    async def test_handle_answer_deleted(self, answers_consumer, project_service):
        task_id = uuid4()
        message = AsyncMock()
        message.value = json.dumps({
            "type": "answer.deleted",
            "task_id": str(task_id)
        }).encode('utf-8')

        await answers_consumer._handle_message(message)

        project_service.decrement_task_answer.assert_awaited_once_with(task_id)

    async def test_handle_missing_task_id(self, answers_consumer, project_service):
        message = AsyncMock()
        message.value = json.dumps({
            "type": "answer.created"
        }).encode('utf-8')

        await answers_consumer._handle_message(message)

        project_service.increment_task_answer.assert_not_awaited()

    async def test_handle_invalid_json(self, answers_consumer, project_service):
        message = AsyncMock()
        message.value = b"invalid json"

        await answers_consumer._handle_message(message)

        project_service.increment_task_answer.assert_not_awaited()
