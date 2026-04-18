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
        updated_at=datetime.now(),
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


@pytest.mark.unit
class TestCreateTask:
    @pytest.mark.asyncio
    async def test_create_task(self, service, repo):
        task = make_task()

        await service.create_task(task)

        repo.create_task.assert_awaited_once_with(task)

    @pytest.mark.asyncio
    async def test_create_task_project_not_found(self, service, repo):
        task = make_task()
        repo.create_task.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.create_task(task)


@pytest.mark.unit
class TestUpdateTask:
    @pytest.mark.asyncio
    async def test_update_task(self, service, repo):
        task = make_task()

        await service.update_task(task)

        repo.update_task.assert_awaited_once_with(task)

    @pytest.mark.asyncio
    async def test_update_task_project_not_found(self, service, repo):
        task = make_task()
        repo.update_task.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.update_task(task)

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, service, repo):
        task = make_task()
        repo.update_task.side_effect = adapter_errors.TaskNotFoundError

        with pytest.raises(project_errors.TaskNotFoundError):
            await service.update_task(task)


@pytest.mark.unit
class TestGetProjectTasks:
    @pytest.mark.asyncio
    async def test_get_project_tasks(self, service, repo):
        project_id = uuid4()
        tasks = [make_task(project_id=project_id) for _ in range(3)]
        repo.get_project_tasks.return_value = tasks

        result = await service.get_project_tasks(project_id)

        repo.get_project_tasks.assert_awaited_once_with(project_id)
        assert result == tasks

    @pytest.mark.asyncio
    async def test_get_project_tasks_project_not_found(self, service, repo):
        project_id = uuid4()
        repo.get_project_tasks.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.get_project_tasks(project_id)

    @pytest.mark.asyncio
    async def test_get_project_tasks_task_not_found(self, service, repo):
        project_id = uuid4()
        repo.get_project_tasks.side_effect = adapter_errors.TaskNotFoundError

        with pytest.raises(project_errors.TaskNotFoundError):
            await service.get_project_tasks(project_id)
