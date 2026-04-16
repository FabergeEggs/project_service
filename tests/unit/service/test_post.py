from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.models.project import Post

from src.services.project_service import ProjectService
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors


def make_post(**kwargs) -> Post:
    default = dict(
        post_id=uuid4(),
        project_id=uuid4(),
        label="Test Post",
        creator="test_user",
        short_description="Short post description",
        description="Full detailed post description for testing",
        created_at=datetime.now()
    )
    default.update(kwargs)
    return Post(**default)


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
