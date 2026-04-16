from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.models.project import Project, Tag, ProjectStatusEnum

from src.services.project_service import ProjectService
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors


def make_project(**kwargs) -> Project:
    default = dict(
        id=uuid4(),
        label="Test Project",
        creator="test_user",
        short_description="Short test description",
        description="Full detailed description for testing purposes",
        tags=[Tag(tag_id=uuid4(), name="test_tag")],
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


@pytest.mark.unit
class TestCreateProject:
    @pytest.mark.asyncio
    async def test_create_project(self, service, repo, kafka):
        project = make_project()

        result = await service.create_project(project)

        repo.create_project.assert_awaited_once_with(project)
        kafka.send_create_project.assert_awaited_once_with(project)
        assert result == project.id

    @pytest.mark.asyncio
    async def test_create_project_already_exists(self, service, repo):
        project = make_project()
        repo.create_project.side_effect = adapter_errors.ProjectAlreadyExistsError

        with pytest.raises(project_errors.ProjectAlreadyExistsError):
            await service.create_project(project)


@pytest.mark.unit
class TestUpdateProject:
    @pytest.mark.asyncio
    async def test_update_project(self, service, repo, kafka):
        project = make_project()

        await service.update_project(project)

        repo.update_project.assert_awaited_once_with(project)
        kafka.send_update_project.assert_called_once_with(project)

    @pytest.mark.asyncio
    async def test_update_project_not_found(self, service, repo):
        project = make_project()
        repo.update_project.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.update_project(project)


@pytest.mark.unit
class TestGetProjectInfo:
    @pytest.mark.asyncio
    async def test_get_project_info(self, service, repo):
        project = make_project()
        repo.get_project_info.return_value = project

        result = await service.get_project_info(project.id)

        repo.get_project_info.assert_awaited_once_with(project.id)
        assert result == project

    @pytest.mark.asyncio
    async def test_get_project_info_not_found(self, service, repo):
        project_id = uuid4()
        repo.get_project_info.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.get_project_info(project_id)


@pytest.mark.unit
class TestGetProjectStatistics:
    @pytest.mark.asyncio
    async def test_get_project_statistics(self, service, repo):
        project_id = uuid4()
        statistics = [10, 5, 3]
        repo.get_project_statistics.return_value = statistics

        result = await service.get_project_statistics(project_id)

        repo.get_project_statistics.assert_awaited_once_with(project_id)
        assert result == statistics

    @pytest.mark.asyncio
    async def test_get_project_statistics_not_found(self, service, repo):
        project_id = uuid4()
        repo.get_project_statistics.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.get_project_statistics(project_id)


@pytest.mark.unit
class TestGetProjects:
    @pytest.mark.asyncio
    async def test_get_projects(self, service, repo):
        project1 = make_project()
        project2 = make_project()
        repo.get_projects.return_value = [project1, project2]
        ids = [project1.id, project2.id]

        result = await service.get_projects(ids)

        repo.get_projects.assert_awaited_once_with(ids)
        assert result == [project1, project2]

    @pytest.mark.asyncio
    async def test_get_projects_not_found(self, service, repo):
        ids = [uuid4(), uuid4()]
        repo.get_projects.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.get_projects(ids)
