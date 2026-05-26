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
        role=ProjectRoleEnum.VOLUNTEER
    )
    default.update(kwargs)
    return DenormUser(**default)


from tests.unit.conftest import make_project_info as make_project_mock


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
        user_id = uuid4()
        memberships = [[uuid4(), uuid4()], [uuid4()]]
        repo.get_user_memberships.return_value = memberships

        result = await service.get_user_memberships(user_id)

        repo.get_user_memberships.assert_awaited_once_with(user_id)
        assert result == memberships

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
        project = make_project_mock(id=project_id)
        repo.get_project_info.return_value = project

        await service.add_member(project_id, user)

        repo.get_project_info.assert_awaited_once_with(project_id)
        repo.add_member.assert_awaited_once_with(project_id, user)

    @pytest.mark.asyncio
    async def test_add_member_project_deleted(self, service, repo):
        user = make_denorm_user()
        project_id = uuid4()
        project = make_project_mock(id=project_id, status="DELETED")
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.add_member(project_id, user)

    @pytest.mark.asyncio
    async def test_add_member_project_finished(self, service, repo):
        user = make_denorm_user()
        project_id = uuid4()
        project = make_project_mock(id=project_id, status="FINISHED")
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectFinishedError):
            await service.add_member(project_id, user)

    @pytest.mark.asyncio
    async def test_add_member_project_not_found(self, service, repo):
        user = make_denorm_user()
        project_id = uuid4()
        repo.get_project_info.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.add_member(project_id, user)

    @pytest.mark.asyncio
    async def test_add_member_already_exists(self, service, repo):
        user = make_denorm_user()
        project_id = uuid4()
        project = make_project_mock(id=project_id)
        repo.get_project_info.return_value = project
        repo.add_member.side_effect = adapter_errors.UserAlreadyExistsError

        with pytest.raises(project_errors.UserAlreadyExistsError):
            await service.add_member(project_id, user)


@pytest.mark.unit
class TestRemoveMember:
    @pytest.mark.asyncio
    async def test_remove_member(self, service, repo):
        user_id = uuid4()
        project_id = uuid4()
        project = make_project_mock(id=project_id)
        repo.get_project_info.return_value = project

        await service.remove_member(project_id, user_id)

        repo.get_project_info.assert_awaited_once_with(project_id)
        repo.remove_member.assert_awaited_once_with(project_id, user_id)

    @pytest.mark.asyncio
    async def test_remove_member_project_deleted(self, service, repo):
        user_id = uuid4()
        project_id = uuid4()
        project = make_project_mock(id=project_id, status="DELETED")
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectDeletedError):
            await service.remove_member(project_id, user_id)

    @pytest.mark.asyncio
    async def test_remove_member_project_finished(self, service, repo):
        user_id = uuid4()
        project_id = uuid4()
        project = make_project_mock(id=project_id, status="FINISHED")
        repo.get_project_info.return_value = project

        with pytest.raises(project_errors.ProjectFinishedError):
            await service.remove_member(project_id, user_id)

    @pytest.mark.asyncio
    async def test_remove_member_project_not_found(self, service, repo):
        user_id = uuid4()
        project_id = uuid4()
        repo.get_project_info.side_effect = adapter_errors.ProjectNotFoundError

        with pytest.raises(project_errors.ProjectNotFoundError):
            await service.remove_member(project_id, user_id)

    @pytest.mark.asyncio
    async def test_remove_member_user_not_found(self, service, repo):
        user_id = uuid4()
        project_id = uuid4()
        project = make_project_mock(id=project_id)
        repo.get_project_info.return_value = project
        repo.remove_member.side_effect = adapter_errors.UserNotFoundError

        with pytest.raises(project_errors.UserNotFoundError):
            await service.remove_member(project_id, user_id)


@pytest.mark.unit
class TestUpsertDenormUser:
    @pytest.mark.asyncio
    async def test_upsert_denorm_user_success(self, service, repo):
        user = make_denorm_user()

        await service.upsert_denorm_user(
            user.id,
            {"name": user.name},
            {"role": user.role},
        )

        repo.upsert_denorm_user.assert_awaited_once_with(
            user.id,
            {"name": user.name},
            {"role": user.role},
        )

    @pytest.mark.asyncio
    async def test_upsert_denorm_user_not_found(self, service, repo):
        user = make_denorm_user()
        repo.upsert_denorm_user.side_effect = adapter_errors.UserNotFoundError

        with pytest.raises(project_errors.UserNotFoundError):
            await service.upsert_denorm_user(
                user.id,
                {"name": user.name},
                {"role": user.role},
            )
