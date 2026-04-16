from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.models.project import Task, TaskStatusEnum
from src.services.project_service import ProjectService
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors


def make_task(**kwargs) -> Task:
    default = dict(
        task_id=uuid4(),
        project_id=uuid4(),
        label="Test Task",
        creator="test_user",
        short_description="Short task description",
        description="Full detailed task description for testing",
        created_at=datetime.now(),
        status=TaskStatusEnum.ACTIVE,
        answers_count=0
    )
    default.update(kwargs)
    return Task(**default)


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def kafka():
    return AsyncMock()


@pytest.fixture
def service(repo, kafka):
    return ProjectService(
        project_repository=repo, kafka_producer=kafka,
    )
