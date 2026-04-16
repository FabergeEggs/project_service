from uuid import UUID, uuid4
from unittest.mock import AsyncMock

import pytest

from datetime import datetime
from src.models.project import DenormUser, ProjectRoleEnum, Project, ProjectStatusEnum, Tag
from src.services.project_service import ProjectService
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors


def make_denorm_user(**kwargs) -> DenormUser:
    default = dict(
        id=uuid4(),
        name="Test User",
        role=ProjectRoleEnum.VOLUNTEER,
        avatar_link="https://example.com/avatar.jpg"
    )
    default.update(kwargs)
    return DenormUser(**default)


def make_profile(**kwargs) -> Project:
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
class TestGetUserMemberships:
    @pytest.mark.asyncio
    async def test_get_user_memberships(self, service, repo):
        user = make_denorm_user()
        repo.get_user_memberships.return_value = user

        result = await service.get_user_memberships(user.id)

        repo.get_user_memberships.assert_awaited_once_with(user.id)
        assert result == user

    @pytest.mark.asyncio
    async def test_get_user_memberships_not_found(self, service, repo):
        user_id = uuid4()
        repo.get_user_memberships.side_effect = adapter_errors.UserNotFoundError

        with pytest.raises(project_errors.UserNotFoundError):
            await service.get_user_memberships(user_id)


@pytest.mark.unit
class TestAddMember:
    @pytest.mark.asyncio
    async def test_add_member(self, service, repo):
        user = make_denorm_user()
        project_id = uuid4()

        await service.add_member(project_id, user)

        repo.add_member.assert_awaited_once_with(project_id, user)

    @pytest.mark.asyncio
    async def test_add_member_project_not_found(self, service, repo):
        user = make_denorm_user()
        project_id = uuid4()
        repo.add_member.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.add_member(project_id, user)

    @pytest.mark.asyncio
    async def test_add_member_already_exists(self, service, repo):
        user = make_denorm_user()
        project_id = uuid4()
        repo.add_member.side_effect = adapter_errors.UserAlreadyExistsError

        with pytest.raises(project_errors.UserAlreadyExistsError):
            await service.add_member(project_id, user)


@pytest.mark.unit
class TestRemoveMember:
    @pytest.mark.asyncio
    async def test_remove_member(self, service, repo):
        user_id = uuid4()
        project_id = uuid4()

        await service.remove_member(project_id, user_id)

        repo.remove_member.assert_awaited_once_with(project_id, user_id)

    @pytest.mark.asyncio
    async def test_remove_member_project_not_found(self, service, repo):
        user_id = uuid4()
        project_id = uuid4()
        repo.remove_member.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.remove_member(project_id, user_id)

    @pytest.mark.asyncio
    async def test_remove_member_user_not_found(self, service, repo):
        user_id = uuid4()
        project_id = uuid4()
        repo.remove_member.side_effect = adapter_errors.UserNotFoundError

        with pytest.raises(project_errors.UserNotFoundError):
            await service.remove_member(project_id, user_id)

    @pytest.mark.asyncio
    async def test_remove_member_already_exists(self, service, repo):
        user_id = uuid4()
        project_id = uuid4()
        repo.remove_member.side_effect = adapter_errors.UserAlreadyExistsError

        with pytest.raises(project_errors.UserAlreadyExistsError):
            await service.remove_member(project_id, user_id)
