from typing import Optional
from uuid import uuid4, UUID
from datetime import datetime
from unittest.mock import AsyncMock
import pytest
from src.models.project import Project, Tag, ProjectStatusEnum
from src.services.project_service import ProjectService
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors


def make_project(
    id: Optional[UUID] = None,
    status: ProjectStatusEnum = ProjectStatusEnum.ACTIVE
) -> Project:
    return Project(
        id=id or uuid4(),
        label="Test Project",
        creator_id=uuid4(),
        short_description="Short test description",
        description="Full detailed description for testing purposes",
        tags=[Tag(tag_id=uuid4(), name="test_tag")],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status=status
    )


def make_project_dict(
    id: Optional[UUID] = None,
    status: ProjectStatusEnum = ProjectStatusEnum.ACTIVE
) -> dict:
    project_id = id or uuid4()
    return {
        "id": project_id,
        "label": "Test Project",
        "creator_id": uuid4(),
        "creator_name": "Test Creator",
        "short_description": "Short test description",
        "description": "Full detailed description for testing purposes",
        "tags": [],
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "status": status
    }


def make_tag() -> Tag:
    return Tag(
        tag_id=uuid4(),
        name="test_tag",
        quantity_count=0
    )


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
        repo.get_project_info.return_value = make_project_dict(id=project.id)

        await service.update_project(project)

        repo.get_project_info.assert_awaited_once_with(project.id)
        repo.update_project.assert_awaited_once_with(project)
        kafka.send_update_project.assert_called_once_with(project)

    @pytest.mark.asyncio
    async def test_update_project_deleted(self, service, repo):
        project = make_project(status=ProjectStatusEnum.DELETED)
        repo.get_project_info.return_value = make_project_dict(
            id=project.id, status=ProjectStatusEnum.DELETED)

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.update_project(project)

    @pytest.mark.asyncio
    async def test_update_project_finished(self, service, repo):
        project = make_project(status=ProjectStatusEnum.FINISHED)
        repo.get_project_info.return_value = make_project_dict(
            id=project.id, status=ProjectStatusEnum.FINISHED)

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
        project = make_project_dict()
        repo.get_project_info.return_value = {
            "id": project["id"],
            "label": project["label"],
            "description": project["description"],
            "creator_id": project["creator_id"],
            "creator_name": "Test Creator",
            "status": project["status"],
            "created_at": project["created_at"],
            "updated_at": project["updated_at"],
            "tags": []
        }

        result = await service.get_project_info(project["id"])

        repo.get_project_info.assert_awaited_once_with(project["id"])
        assert result["id"] == project["id"]
        assert result["status"] == project["status"]

    @pytest.mark.asyncio
    async def test_get_project_info_deleted(self, service, repo):
        project = make_project_dict(status=ProjectStatusEnum.DELETED)
        repo.get_project_info.return_value = {
            "id": project["id"],
            "label": project["label"],
            "description": project["description"],
            "creator_id": project["creator_id"],
            "creator_name": "Test Creator",
            "status": ProjectStatusEnum.DELETED,
            "created_at": project["created_at"],
            "updated_at": project["updated_at"],
            "tags": []
        }

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.get_project_info(project["id"])

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
        project_dict = make_project_dict(id=project_id)
        statistics = {"project_id": str(
            project_id), "tasks_count": 5, "members_count": 3, "answers_count": 10}
        repo.get_project_info.return_value = project_dict
        repo.get_project_statistics.return_value = statistics

        result = await service.get_project_statistics(project_id)

        repo.get_project_info.assert_awaited_once_with(project_id)
        repo.get_project_statistics.assert_awaited_once_with(project_id)
        assert result == statistics

    @pytest.mark.asyncio
    async def test_get_project_statistics_deleted(self, service, repo):
        project_id = uuid4()
        project_dict = make_project_dict(
            id=project_id, status=ProjectStatusEnum.DELETED)
        repo.get_project_info.return_value = project_dict

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
        project1 = make_project_dict()
        project2 = make_project_dict()
        repo.get_projects.return_value = [project1, project2]
        ids = [project1["id"], project2["id"]]

        result = await service.get_projects(ids)

        repo.get_projects.assert_awaited_once_with(ids)
        assert result == [project1, project2]

    @pytest.mark.asyncio
    async def test_get_projects_with_deleted(self, service, repo):
        project1 = make_project_dict()
        project2 = make_project_dict(status=ProjectStatusEnum.DELETED)
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
        project = make_project(status=ProjectStatusEnum.ACTIVE)
        project_dict = make_project_dict(
            id=project.id, status=ProjectStatusEnum.ACTIVE)
        repo.get_project_info.return_value = project_dict

        result = await service._check_project_active(project.id)

        assert result == project_dict

    @pytest.mark.asyncio
    async def test_check_active_deleted(self, service, repo):
        project = make_project(status=ProjectStatusEnum.DELETED)
        project_dict = make_project_dict(
            id=project.id, status=ProjectStatusEnum.DELETED)
        repo.get_project_info.return_value = project_dict

        with pytest.raises(project_errors.ProjectDeletedError):
            await service._check_project_active(project.id)

    @pytest.mark.asyncio
    async def test_check_active_finished(self, service, repo):
        project = make_project(status=ProjectStatusEnum.FINISHED)
        project_dict = make_project_dict(
            id=project.id, status=ProjectStatusEnum.FINISHED)
        repo.get_project_info.return_value = project_dict

        with pytest.raises(project_errors.ProjectFinishedError):
            await service._check_project_active(project.id)

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
        project = make_project(status=ProjectStatusEnum.ACTIVE)
        project_dict = make_project_dict(
            id=project.id, status=ProjectStatusEnum.ACTIVE)
        repo.get_project_info.return_value = project_dict

        result = await service._check_project_accessible(project.id)

        assert result == project_dict

    @pytest.mark.asyncio
    async def test_accessible_finished_allowed(self, service, repo):
        """Для доступности finished проект разрешён"""
        project = make_project(status=ProjectStatusEnum.FINISHED)
        project_dict = make_project_dict(
            id=project.id, status=ProjectStatusEnum.FINISHED)
        repo.get_project_info.return_value = project_dict

        result = await service._check_project_accessible(project.id)

        assert result == project_dict

    @pytest.mark.asyncio
    async def test_accessible_deleted(self, service, repo):
        project = make_project(status=ProjectStatusEnum.DELETED)
        project_dict = make_project_dict(
            id=project.id, status=ProjectStatusEnum.DELETED)
        repo.get_project_info.return_value = project_dict

        with pytest.raises(project_errors.ProjectDeletedError):
            await service._check_project_accessible(project.id)
