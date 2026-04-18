from src.models.project import Post
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
        created_at=datetime.now(),
        updated_at=datetime.now(),
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
    async def test_create_post(self, service, repo):
        post = make_post()

        await service.create_post(post)

        repo.create_post.assert_awaited_once_with(post)

    @pytest.mark.asyncio
    async def test_create_post_project_not_found(self, service, repo):
        post = make_post()
        repo.create_post.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.create_post(post)


@pytest.mark.unit
class TestUpdatePost:
    @pytest.mark.asyncio
    async def test_update_post(self, service, repo):
        post = make_post()

        await service.update_post(post)

        repo.update_post.assert_awaited_once_with(post)

    @pytest.mark.asyncio
    async def test_update_post_project_not_found(self, service, repo):
        post = make_post()
        repo.update_post.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.update_post(post)

    @pytest.mark.asyncio
    async def test_update_post_not_found(self, service, repo):
        post = make_post()
        repo.update_post.side_effect = adapter_errors.PostNotFoundError

        with pytest.raises(project_errors.PostNotFoundError):
            await service.update_post(post)


@pytest.mark.unit
class TestGetProjectPosts:
    @pytest.mark.asyncio
    async def test_get_project_posts(self, service, repo):
        project_id = uuid4()
        posts = [make_post(project_id=project_id) for _ in range(3)]
        repo.get_project_posts.return_value = posts

        result = await service.get_project_posts(project_id)

        repo.get_project_posts.assert_awaited_once_with(project_id)
        assert result == posts

    @pytest.mark.asyncio
    async def test_get_project_posts_project_not_found(self, service, repo):
        project_id = uuid4()
        repo.get_project_posts.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.get_project_posts(project_id)

    @pytest.mark.asyncio
    async def test_get_project_posts_post_not_found(self, service, repo):
        project_id = uuid4()
        repo.get_project_posts.side_effect = adapter_errors.PostNotFoundError

        with pytest.raises(project_errors.PostNotFoundError):
            await service.get_project_posts(project_id)


@pytest.mark.unit
class TestDeletePost:
    @pytest.mark.asyncio
    async def test_delete_post(self, service, repo):
        post_id = uuid4()

        await service.delete_post(post_id)

        repo.delete_post.assert_awaited_once_with(post_id)

    @pytest.mark.asyncio
    async def test_delete_post_project_not_found(self, service, repo):
        post_id = uuid4()
        repo.delete_post.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.delete_post(post_id)

    @pytest.mark.asyncio
    async def test_delete_post_not_found(self, service, repo):
        post_id = uuid4()
        repo.delete_post.side_effect = adapter_errors.PostNotFoundError

        with pytest.raises(project_errors.PostNotFoundError):
            await service.delete_post(post_id)
