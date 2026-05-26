from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import AsyncMock
import pytest
from src.models.project import Project, Tag, ProjectStatusEnum
from src.services.project_service import ProjectService
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors
from tests.unit.conftest import make_project, make_project_info


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
        kafka.send_create_project.assert_called_once_with(project)
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
        repo.get_project_info.return_value = make_project_info(
            id=project.id, status=project.status
        )

        await service.update_project(project)

        repo.get_project_info.assert_awaited_once_with(project.id)
        repo.update_project.assert_awaited_once_with(project)
        kafka.send_update_project.assert_called_once_with(project)

    @pytest.mark.asyncio
    async def test_update_project_deleted(self, service, repo):
        project = make_project(status=ProjectStatusEnum.DELETED)
        repo.get_project_info.return_value = make_project_info(
            id=project.id, status=ProjectStatusEnum.DELETED
        )

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.update_project(project)

    @pytest.mark.asyncio
    async def test_update_project_finished(self, service, repo):
        project = make_project(status=ProjectStatusEnum.FINISHED)
        repo.get_project_info.return_value = make_project_info(
            id=project.id, status=ProjectStatusEnum.FINISHED
        )

        with pytest.raises(project_errors.ProjectFinishedError):
            await service.update_project(project)

    @pytest.mark.asyncio
    async def test_update_project_not_found(self, service, repo):
        project = make_project()
        repo.get_project_info.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.update_project(project)


@pytest.mark.unit
class TestGetProjectInfo:
    @pytest.mark.asyncio
    async def test_get_project_info(self, service, repo):
        project = make_project()
        repo.get_project_info.return_value = {
            "id": project.id,
            "label": project.label,
            "description": project.description,
            "creator_id": project.creator_id,
            "creator_name": "Test Creator",
            "status": project.status,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "tags": []
        }

        result = await service.get_project_info(project.id)

        repo.get_project_info.assert_awaited_once_with(project.id)
        assert result["id"] == project.id
        assert result["status"] == project.status

    @pytest.mark.asyncio
    async def test_get_project_info_deleted(self, service, repo):
        project = make_project(status=ProjectStatusEnum.DELETED)
        repo.get_project_info.return_value = {
            "id": project.id,
            "label": project.label,
            "description": project.description,
            "creator_id": project.creator_id,
            "creator_name": "Test Creator",
            "status": ProjectStatusEnum.DELETED,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "tags": []
        }

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.get_project_info(project.id)

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
        project = make_project(id=project_id)
        statistics = {"project_id": str(
            project_id), "tasks_count": 5, "members_count": 3, "answers_count": 10}
        repo.get_project_info.return_value = make_project_info(
            id=project_id, status=project.status
        )
        repo.get_project_statistics.return_value = statistics

        result = await service.get_project_statistics(project_id)

        repo.get_project_info.assert_awaited_once_with(project_id)
        repo.get_project_statistics.assert_awaited_once_with(project_id)
        assert result == statistics

    @pytest.mark.asyncio
    async def test_get_project_statistics_deleted(self, service, repo):
        project_id = uuid4()
        make_project(id=project_id, status=ProjectStatusEnum.DELETED)
        repo.get_project_info.return_value = make_project_info(
            id=project_id, status=ProjectStatusEnum.DELETED
        )

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.get_project_statistics(project_id)

    @pytest.mark.asyncio
    async def test_get_project_statistics_not_found(self, service, repo):
        project_id = uuid4()
        repo.get_project_info.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.get_project_statistics(project_id)


@pytest.mark.unit
class TestGetProjects:
    @pytest.mark.asyncio
    async def test_get_projects(self, service, repo):
        project1 = make_project_info()
        project2 = make_project_info()
        repo.get_projects.return_value = [project1, project2]
        ids = [project1["id"], project2["id"]]

        result = await service.get_projects(ids)

        repo.get_projects.assert_awaited_once_with(ids)
        assert result == [project1, project2]

    @pytest.mark.asyncio
    async def test_get_projects_with_deleted(self, service, repo):
        project1 = make_project_info()
        project2 = make_project_info(status=ProjectStatusEnum.DELETED)
        repo.get_projects.return_value = [project1, project2]
        ids = [project1["id"], project2["id"]]

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.get_projects(ids)

    @pytest.mark.asyncio
    async def test_get_projects_not_found(self, service, repo):
        ids = [uuid4(), uuid4()]
        repo.get_projects.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.get_projects(ids)


@pytest.mark.unit
class TestCheckProjectActive:
    @pytest.mark.asyncio
    async def test_check_active_success(self, service, repo):
        project = make_project_info(status=ProjectStatusEnum.ACTIVE)
        repo.get_project_info.return_value = project

        result = await service._check_project_active(project["id"])

        assert result == project

    @pytest.mark.asyncio
    async def test_check_active_deleted(self, service, repo):
        project = make_project_info(status=ProjectStatusEnum.DELETED)
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectDeletedError):
            await service._check_project_active(project["id"])

    @pytest.mark.asyncio
    async def test_check_active_finished(self, service, repo):
        project = make_project_info(status=ProjectStatusEnum.FINISHED)
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectFinishedError):
            await service._check_project_active(project["id"])

    @pytest.mark.asyncio
    async def test_check_active_not_found(self, service, repo):
        project_id = uuid4()
        repo.get_project_info.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service._check_project_active(project_id)


@pytest.mark.unit
class TestCheckProjectAccessible:
    @pytest.mark.asyncio
    async def test_accessible_success(self, service, repo):
        project = make_project_info(status=ProjectStatusEnum.ACTIVE)
        repo.get_project_info.return_value = project

        result = await service._check_project_accessible(project["id"])

        assert result == project

    @pytest.mark.asyncio
    async def test_accessible_finished_allowed(self, service, repo):
        """Для доступности finished проект разрешён"""
        project = make_project_info(status=ProjectStatusEnum.FINISHED)
        repo.get_project_info.return_value = project

        result = await service._check_project_accessible(project["id"])

        assert result == project

    @pytest.mark.asyncio
    async def test_accessible_deleted(self, service, repo):
        project = make_project_info(status=ProjectStatusEnum.DELETED)
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectDeletedError):
            await service._check_project_accessible(project["id"])
