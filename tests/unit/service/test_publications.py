
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest
from src.services.project_service import ProjectService, ProjectStatusEnum
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors


def make_publication(**kwargs):
    default = dict(
        id=uuid4(),
        project_id=uuid4(),
        label="Test Publication",
        short_description="Short description",
        created_at=datetime.now(timezone.utc),
        creator_id=uuid4(),
        creator_name="Test Creator",
        type="task",
        answers_count=5,
        status="ACTIVE"
    )
    default.update(kwargs)
    return default


def make_project_mock(**kwargs) -> dict:
    return {
        "id": kwargs.get("id", uuid4()),
        "status": kwargs.get("status", ProjectStatusEnum.ACTIVE),
    }


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


@pytest.mark.unit
class TestGetPublications:
    @pytest.mark.asyncio
    async def test_get_publications_success(self, service, repo):
        project_id = uuid4()
        project = make_project_mock(id=project_id)
        publications = [make_publication() for _ in range(3)]

        repo.get_project_info.return_value = project
        repo.get_project_publications.return_value = publications

        result = await service.get_publications(project_id, limit=10, cursor=None)

        repo.get_project_info.assert_awaited_once_with(project_id)
        repo.get_project_publications.assert_awaited_once_with(
            project_id, 10, None)
        assert result == publications
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_publications_with_cursor(self, service, repo):
        project_id = uuid4()
        project = make_project_mock(id=project_id)
        cursor_date = datetime.now(timezone.utc)
        publications = [make_publication() for _ in range(2)]

        repo.get_project_info.return_value = project
        repo.get_project_publications.return_value = publications

        result = await service.get_publications(project_id, limit=5, cursor=cursor_date)

        repo.get_project_publications.assert_awaited_once_with(
            project_id, 5, cursor_date)
        assert result == publications

    @pytest.mark.asyncio
    async def test_get_publications_empty(self, service, repo):
        project_id = uuid4()
        project = make_project_mock(id=project_id)

        repo.get_project_info.return_value = project
        repo.get_project_publications.return_value = []

        result = await service.get_publications(project_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_publications_project_deleted(self, service, repo):
        project_id = uuid4()
        project = make_project_mock(id=project_id, status="DELETED")

        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.get_publications(project_id)

        repo.get_project_publications.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_publications_project_not_found(self, service, repo):
        project_id = uuid4()

        repo.get_project_info.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.get_publications(project_id)

        repo.get_project_publications.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_publications_mixed_types(self, service, repo):
        project_id = uuid4()
        project = make_project_mock(id=project_id)
        publications = [
            make_publication(type="task"),
            make_publication(type="post")
        ]
        repo.get_project_info.return_value = project
        repo.get_project_publications.return_value = publications

        result = await service.get_publications(project_id)

        assert len(result) == 2
        types = [p["type"] for p in result]
        assert "task" in types
        assert "post" in types
