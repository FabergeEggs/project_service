from src.models.project import Post
from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from src.services.project_service import ProjectService
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors


def make_post(**kwargs) -> Post:
    default = dict(
        post_id=uuid4(),
        project_id=uuid4(),
        creator_id=uuid4(),
        label="Test Post",
        creator="test_user",
        short_description="Short post description",
        description="Full detailed post description for testing",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    default.update(kwargs)
    return Post(**default)


def make_project_mock(**kwargs):
    class MockProject:
        def __init__(self):
            self.id = kwargs.get("id", uuid4())
            self.status = kwargs.get("status", "ACTIVE")
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
class TestCreatePost:
    @pytest.mark.asyncio
    async def test_create_post(self, service, repo, kafka):
        post = make_post()
        project = make_project_mock(id=post.project_id)
        repo.get_project_info.return_value = project

        await service.create_post(post)

        repo.get_project_info.assert_awaited_once_with(post.project_id)
        repo.create_post.assert_awaited_once_with(post)
        kafka.send_create_post.assert_called_once_with(post)

    @pytest.mark.asyncio
    async def test_create_post_project_deleted(self, service, repo):
        post = make_post()
        project = make_project_mock(id=post.project_id, status="DELETED")
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.create_post(post)

    @pytest.mark.asyncio
    async def test_create_post_project_finished(self, service, repo):
        post = make_post()
        project = make_project_mock(id=post.project_id, status="FINISHED")
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectFinishedError):
            await service.create_post(post)

    @pytest.mark.asyncio
    async def test_create_post_project_not_found(self, service, repo):
        post = make_post()
        repo.get_project_info.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.create_post(post)


@pytest.mark.unit
class TestUpdatePost:
    @pytest.mark.asyncio
    async def test_update_post(self, service, repo, kafka):
        post = make_post()
        project = make_project_mock(id=post.project_id)
        repo.get_project_info.return_value = project

        await service.update_post(post)

        repo.get_project_info.assert_awaited_once_with(post.project_id)
        repo.update_post.assert_awaited_once_with(post)
        kafka.send_update_post.assert_called_once_with(post)

    @pytest.mark.asyncio
    async def test_update_post_project_deleted(self, service, repo):
        post = make_post()
        project = make_project_mock(id=post.project_id, status="DELETED")
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.update_post(post)

    @pytest.mark.asyncio
    async def test_update_post_project_finished(self, service, repo):
        post = make_post()
        project = make_project_mock(id=post.project_id, status="FINISHED")
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectFinishedError):
            await service.update_post(post)

    @pytest.mark.asyncio
    async def test_update_post_project_not_found(self, service, repo):
        post = make_post()
        repo.get_project_info.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.update_post(post)

    @pytest.mark.asyncio
    async def test_update_post_not_found(self, service, repo):
        post = make_post()
        project = make_project_mock(id=post.project_id)
        repo.get_project_info.return_value = project
        repo.update_post.side_effect = adapter_errors.PostNotFoundError

        with pytest.raises(project_errors.PostNotFoundError):
            await service.update_post(post)


@pytest.mark.unit
class TestDeletePost:
    @pytest.mark.asyncio
    async def test_delete_post(self, service, repo, kafka):
        post_id = uuid4()
        post = make_post(post_id=post_id)
        project = make_project_mock(id=post.project_id)
        repo.get_post.return_value = post
        repo.get_project_info.return_value = project

        await service.delete_post(post_id)

        repo.get_post.assert_awaited_once_with(post_id)
        repo.get_project_info.assert_awaited_once_with(post.project_id)
        repo.delete_post.assert_awaited_once_with(post_id)
        kafka.send_delete_post.assert_called_once_with(post_id)

    @pytest.mark.asyncio
    async def test_delete_post_project_deleted(self, service, repo):
        post_id = uuid4()
        post = make_post(post_id=post_id)
        project = make_project_mock(id=post.project_id, status="DELETED")
        repo.get_post.return_value = post
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.delete_post(post_id)

    @pytest.mark.asyncio
    async def test_delete_post_project_finished(self, service, repo):
        post_id = uuid4()
        post = make_post(post_id=post_id)
        project = make_project_mock(id=post.project_id, status="FINISHED")
        repo.get_post.return_value = post
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectFinishedError):
            await service.delete_post(post_id)

    @pytest.mark.asyncio
    async def test_delete_post_not_found(self, service, repo):
        post_id = uuid4()
        repo.get_post.side_effect = adapter_errors.PostNotFoundError

        with pytest.raises(project_errors.PostNotFoundError):
            await service.delete_post(post_id)


@pytest.mark.unit
class TestGetPost:
    @pytest.mark.asyncio
    async def test_get_post(self, service, repo):
        post = make_post()
        project = make_project_mock(id=post.project_id)
        repo.get_post.return_value = post
        repo.get_project_info.return_value = project

        result = await service.get_post(post.post_id)

        repo.get_post.assert_awaited_once_with(post.post_id)
        repo.get_project_info.assert_awaited_once_with(post.project_id)
        assert result == post

    @pytest.mark.asyncio
    async def test_get_post_project_deleted(self, service, repo):
        post = make_post()
        project = make_project_mock(id=post.project_id, status="DELETED")
        repo.get_post.return_value = post
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.get_post(post.post_id)

    @pytest.mark.asyncio
    async def test_get_post_not_found(self, service, repo):
        post_id = uuid4()
        repo.get_post.side_effect = adapter_errors.PostNotFoundError

        with pytest.raises(project_errors.PostNotFoundError):
            await service.get_post(post_id)
