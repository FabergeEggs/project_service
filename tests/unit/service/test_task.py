from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.models.project import Task, TaskStatusEnum, ProjectStatusEnum
from src.services.project_service import ProjectService
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors


def make_task(**kwargs) -> Task:
    default = dict(
        task_id=uuid4(),
        project_id=uuid4(),
        creator_id=uuid4(),
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


def make_project_mock(**kwargs):
    class MockProject:
        def __init__(self):
            self.id = kwargs.get("id", uuid4())
            self.status = kwargs.get("status", ProjectStatusEnum.ACTIVE)
    return MockProject()


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
        project = make_project_mock(id=task.project_id)
        repo.get_project_info.return_value = project

        await service.create_task(task)

        repo.get_project_info.assert_awaited_once_with(task.project_id)
        repo.create_task.assert_awaited_once_with(task)

    @pytest.mark.asyncio
    async def test_create_task_project_deleted(self, service, repo):
        task = make_task()
        project = make_project_mock(
            id=task.project_id, status=ProjectStatusEnum.DELETED)
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.create_task(task)

    @pytest.mark.asyncio
    async def test_create_task_project_finished(self, service, repo):
        task = make_task()
        project = make_project_mock(
            id=task.project_id, status=ProjectStatusEnum.FINISHED)
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectFinishedError):
            await service.create_task(task)

    @pytest.mark.asyncio
    async def test_create_task_project_not_found(self, service, repo):
        task = make_task()
        repo.get_project_info.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.create_task(task)


@pytest.mark.unit
class TestUpdateTask:
    @pytest.mark.asyncio
    async def test_update_task(self, service, repo):
        task = make_task()
        project = make_project_mock(id=task.project_id)
        repo.get_project_info.return_value = project

        await service.update_task(task)

        repo.get_project_info.assert_awaited_once_with(task.project_id)
        repo.update_task.assert_awaited_once_with(task)

    @pytest.mark.asyncio
    async def test_update_task_project_deleted(self, service, repo):
        task = make_task()
        project = make_project_mock(
            id=task.project_id, status=ProjectStatusEnum.DELETED)
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.update_task(task)

    @pytest.mark.asyncio
    async def test_update_task_project_finished(self, service, repo):
        task = make_task()
        project = make_project_mock(
            id=task.project_id, status=ProjectStatusEnum.FINISHED)
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectFinishedError):
            await service.update_task(task)

    @pytest.mark.asyncio
    async def test_update_task_project_not_found(self, service, repo):
        task = make_task()
        repo.get_project_info.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.update_task(task)

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, service, repo):
        task = make_task()
        project = make_project_mock(id=task.project_id)
        repo.get_project_info.return_value = project
        repo.update_task.side_effect = adapter_errors.TaskNotFoundError

        with pytest.raises(project_errors.TaskNotFoundError):
            await service.update_task(task)


@pytest.mark.unit
class TestGetTask:
    @pytest.mark.asyncio
    async def test_get_task(self, service, repo):
        task = make_task()
        project = make_project_mock(id=task.project_id)
        repo.get_task.return_value = task
        repo.get_project_info.return_value = project

        result = await service.get_task(task.task_id)

        repo.get_task.assert_awaited_once_with(task.task_id)
        repo.get_project_info.assert_awaited_once_with(task.project_id)
        assert result == task

    @pytest.mark.asyncio
    async def test_get_task_project_deleted(self, service, repo):
        task = make_task()
        project = make_project_mock(
            id=task.project_id, status=ProjectStatusEnum.DELETED)
        repo.get_task.return_value = task
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.get_task(task.task_id)

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, service, repo):
        task_id = uuid4()
        repo.get_task.side_effect = adapter_errors.TaskNotFoundError

        with pytest.raises(project_errors.TaskNotFoundError):
            await service.get_task(task_id)


@pytest.mark.unit
class TestUpdateTaskAnswers:
    @pytest.mark.asyncio
    async def test_answer_incrementation(self, service, repo):
        task = make_task()

        await service.increment_task_answer(task.task_id)

        repo.increment_task_answer.assert_awaited_once_with(task.task_id)

    @pytest.mark.asyncio
    async def test_answer_incrementation_not_found(self, service, repo):
        task_id = uuid4()

        repo.increment_task_answer.side_effect = adapter_errors.TaskNotFoundError

        with patch("src.services.project_service.logger") as mock_logger:
            await service.increment_task_answer(task_id)

            mock_logger.warning.assert_called_once()
            assert "doesn't exist" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_answer_decrementation(self, service, repo):
        task = make_task(answers_count=1)

        await service.decrement_task_answer(task.task_id)

        repo.decrement_task_answer.assert_awaited_once_with(task.task_id)

    @pytest.mark.asyncio
    async def test_answer_decrementation_not_found(self, service, repo):
        task_id = uuid4()

        repo.decrement_task_answer.side_effect = adapter_errors.TaskNotFoundError

        with patch("src.services.project_service.logger") as mock_logger:
            await service.decrement_task_answer(task_id)

            mock_logger.warning.assert_called_once()
            assert "doesn't exist" in mock_logger.warning.call_args[0][0]
