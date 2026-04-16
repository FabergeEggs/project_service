from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.models.project import Project, Tag, ProjectStatusEnum

from src.services.project_service import ProjectService
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors


def make_profile(**kwargs) -> Project:
    default = dict(
        id=uuid4(),
        label="Test Project",
        creator="test_user",
        short_description="Short test description",
        description="Full detailed description for testing purposes",
        tags=[Tag(id=uuid4(), name="test_tag")],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status=ProjectStatusEnum.ACTIVE
    )
    default.update(kwargs)
    return Project(**default)


def make_tag(**kwargs) -> Tag:
    default = dict(
        tag_id=uuid4(),
        name="test_tag",
        quantity_count=0
    )
    default.update(kwargs)
    return Tag(**default)


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
