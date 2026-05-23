import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.http.project_router import create_project_router
from src.models.project import ProjectStatusEnum, TaskStatusEnum
import src.services.errors as project_errors


USER_ID = uuid.uuid4()
USER_ID_2 = uuid.uuid4()
PROJECT_ID = uuid.uuid4()
TASK_ID = uuid.uuid4()
POST_ID = uuid.uuid4()

AUTH_HEADERS = {
    "X-User-Id": str(USER_ID),
    "X-Username": "testuser",
    "X-User-Roles": "user",
}

OTHER_USER_HEADERS = {
    "X-User-Id": str(USER_ID_2),
    "X-Username": "otheruser",
    "X-User-Roles": "user",
}


def make_project_dict(**kwargs) -> dict:
    defaults = dict(
        id=PROJECT_ID,
        label="Test Project",
        creator_id=USER_ID,
        creator_name="testuser",
        short_description="Short desc",
        description="Full description",
        tags=[],
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status=ProjectStatusEnum.ACTIVE,
    )
    defaults.update(kwargs)
    return defaults


def make_task_dict(**kwargs) -> dict:
    defaults = dict(
        task_id=TASK_ID,
        project_id=PROJECT_ID,
        creator_id=USER_ID,
        creator_name="testuser",
        label="Test Task",
        short_description="Short desc",
        description="Full description",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status=TaskStatusEnum.ACTIVE,
        answers_count=0,
    )
    defaults.update(kwargs)
    return defaults


def make_post_dict(**kwargs) -> dict:
    defaults = dict(
        post_id=POST_ID,
        project_id=PROJECT_ID,
        creator_id=USER_ID,
        creator_name="testuser",
        creator="testuser",
        label="Test Post",
        short_description="Short desc",
        description="Full description",
        comments_count=0,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(kwargs)
    return defaults


def make_project_payload(**kwargs) -> dict:
    defaults = dict(
        label="Test Project",
        short_description="Short desc",
        description="Full description",
        tags=["python", "fastapi"],
        status="ACTIVE",
    )
    defaults.update(kwargs)
    return defaults


def make_task_payload(**kwargs) -> dict:
    defaults = dict(
        project_id=str(PROJECT_ID),
        label="Test Task",
        short_description="Short desc",
        description="Full description",
        status="ACTIVE",
    )
    defaults.update(kwargs)
    return defaults


def make_post_payload(**kwargs) -> dict:
    defaults = dict(
        project_id=str(PROJECT_ID),
        label="Test Post",
        short_description="Short desc",
        description="Full description",
    )
    defaults.update(kwargs)
    return defaults


@pytest.fixture
def service():
    return AsyncMock()


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(create_project_router(service))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.unit
class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_returns_200(self, client):
        async with client as c:
            resp = await c.get("/project/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


@pytest.mark.unit
class TestCreateProject:
    @pytest.mark.asyncio
    async def test_returns_201_with_id(self, client, service):
        project_id = uuid.uuid4()
        service.create_project.return_value = project_id
        async with client as c:
            resp = await c.post("/project", json=make_project_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 201
        assert resp.json()["id"] == str(project_id)

    @pytest.mark.asyncio
    async def test_calls_service(self, client, service):
        service.create_project.return_value = uuid.uuid4()
        async with client as c:
            await c.post("/project", json=make_project_payload(), headers=AUTH_HEADERS)
        service.create_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_401_without_auth_headers(self, client):
        async with client as c:
            resp = await c.post("/project", json=make_project_payload())
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_422_when_label_too_short(self, client):
        async with client as c:
            resp = await c.post("/project", json=make_project_payload(label="ab"), headers=AUTH_HEADERS)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_returns_409_when_project_already_exists(self, client, service):
        service.create_project.side_effect = project_errors.ProjectAlreadyExistsError(
            "exists")
        async with client as c:
            resp = await c.post("/project", json=make_project_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 409


@pytest.mark.unit
class TestGetProjectInfo:
    @pytest.mark.asyncio
    async def test_returns_200_with_project_data(self, client, service):
        service.get_project_info.return_value = make_project_dict()
        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/info")
        assert resp.status_code == 200
        assert resp.json()["label"] == "Test Project"

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self, client, service):
        service.get_project_info.side_effect = project_errors.ProjectNotFoundError(
            "not found")
        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/info")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_deleted(self, client, service):
        service.get_project_info.side_effect = project_errors.ProjectDeletedError(
            "deleted")
        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/info")
        assert resp.status_code == 410


@pytest.mark.unit
class TestGetProjectStatistics:
    @pytest.mark.asyncio
    async def test_returns_200_with_stats(self, client, service):
        service.get_project_statistics.return_value = {
            "project_id": PROJECT_ID,
            "tasks_count": 5,
            "members_count": 10,
            "answers_count": 20,
        }
        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/statistics")
        assert resp.status_code == 200
        assert resp.json()["tasks_count"] == 5
        assert resp.json()["participants_count"] == 10

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self, client, service):
        service.get_project_statistics.side_effect = project_errors.ProjectNotFoundError(
            "not found")
        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/statistics")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_deleted(self, client, service):
        service.get_project_statistics.side_effect = project_errors.ProjectDeletedError(
            "deleted")
        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/statistics")
        assert resp.status_code == 410


@pytest.mark.unit
class TestUpdateProject:
    @pytest.mark.asyncio
    async def test_returns_200_on_success(self, client, service):
        service.get_project_info.return_value = make_project_dict(
            creator_id=USER_ID)
        service.update_project.return_value = None
        async with client as c:
            resp = await c.put(f"/project/{PROJECT_ID}", json=make_project_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Project updated successfully"

    @pytest.mark.asyncio
    async def test_returns_403_when_not_creator(self, client, service):
        service.get_project_info.return_value = make_project_dict(
            creator_id=USER_ID)
        async with client as c:
            resp = await c.put(f"/project/{PROJECT_ID}", json=make_project_payload(), headers=OTHER_USER_HEADERS)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_project_not_found(self, client, service):
        service.get_project_info.side_effect = project_errors.ProjectNotFoundError(
            "not found")
        async with client as c:
            resp = await c.put(f"/project/{PROJECT_ID}", json=make_project_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_400_when_project_finished(self, client, service):
        service.get_project_info.return_value = make_project_dict(
            creator_id=USER_ID)
        service.update_project.side_effect = project_errors.ProjectFinishedError(
            "finished")
        async with client as c:
            resp = await c.put(f"/project/{PROJECT_ID}", json=make_project_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 400


@pytest.mark.unit
class TestGetProjects:
    @pytest.mark.asyncio
    async def test_returns_200_with_list(self, client, service):
        service.get_projects.return_value = [make_project_dict()]
        async with client as c:
            resp = await c.post("/project/batch", json=[str(PROJECT_ID)])
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self, client, service):
        service.get_projects.side_effect = project_errors.ProjectNotFoundError(
            "not found")
        async with client as c:
            resp = await c.post("/project/batch", json=[str(PROJECT_ID)])
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, client, service):
        service.get_projects.return_value = []
        async with client as c:
            resp = await c.post("/project/batch", json=[])
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.unit
class TestCreateTask:
    @pytest.mark.asyncio
    async def test_returns_201_with_id(self, client, service):
        task_id = uuid.uuid4()
        service.get_project_info.return_value = make_project_dict(
            creator_id=USER_ID)
        service.create_task.return_value = task_id
        async with client as c:
            resp = await c.post(f"/project/{PROJECT_ID}/task", json=make_task_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 201
        assert resp.json()["id"] == str(task_id)

    @pytest.mark.asyncio
    async def test_returns_403_when_not_creator(self, client, service):
        service.get_project_info.return_value = make_project_dict(
            creator_id=USER_ID)
        async with client as c:
            resp = await c.post(f"/project/{PROJECT_ID}/task", json=make_task_payload(), headers=OTHER_USER_HEADERS)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_project_not_found(self, client, service):
        service.get_project_info.side_effect = project_errors.ProjectNotFoundError(
            "not found")
        async with client as c:
            resp = await c.post(f"/project/{PROJECT_ID}/task", json=make_task_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_project_deleted(self, client, service):
        service.get_project_info.side_effect = project_errors.ProjectDeletedError(
            "deleted")
        async with client as c:
            resp = await c.post(f"/project/{PROJECT_ID}/task", json=make_task_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 410

    @pytest.mark.asyncio
    async def test_returns_422_when_label_too_short(self, client, service):
        service.get_project_info.return_value = make_project_dict(
            creator_id=USER_ID)
        async with client as c:
            resp = await c.post(f"/project/{PROJECT_ID}/task", json=make_task_payload(label="ab"), headers=AUTH_HEADERS)
        assert resp.status_code == 422


@pytest.mark.unit
class TestUpdateTask:
    @pytest.mark.asyncio
    async def test_returns_200_on_success(self, client, service):
        service.get_task.return_value = make_task_dict(creator_id=USER_ID)
        service.update_task.return_value = None
        async with client as c:
            resp = await c.put(f"/project/{PROJECT_ID}/task/{TASK_ID}", json=make_task_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Task updated successfully"

    @pytest.mark.asyncio
    async def test_returns_403_when_not_creator(self, client, service):
        service.get_task.return_value = make_task_dict(creator_id=USER_ID)
        async with client as c:
            resp = await c.put(f"/project/{PROJECT_ID}/task/{TASK_ID}", json=make_task_payload(), headers=OTHER_USER_HEADERS)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_task_not_found(self, client, service):
        service.get_task.side_effect = project_errors.TaskNotFoundError(
            "not found")
        async with client as c:
            resp = await c.put(f"/project/{PROJECT_ID}/task/{TASK_ID}", json=make_task_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_project_deleted(self, client, service):
        service.get_task.return_value = make_task_dict(creator_id=USER_ID)
        service.update_task.side_effect = project_errors.ProjectDeletedError(
            "deleted")
        async with client as c:
            resp = await c.put(f"/project/{PROJECT_ID}/task/{TASK_ID}", json=make_task_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 410


@pytest.mark.unit
class TestGetTask:
    @pytest.mark.asyncio
    async def test_returns_200_with_task_data(self, client, service):
        service.get_task.return_value = make_task_dict()
        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/task/{TASK_ID}")
        assert resp.status_code == 200
        assert resp.json()["label"] == "Test Task"

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self, client, service):
        service.get_task.side_effect = project_errors.TaskNotFoundError(
            "not found")
        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/task/{TASK_ID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_project_deleted(self, client, service):
        service.get_task.side_effect = project_errors.ProjectDeletedError(
            "deleted")
        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/task/{TASK_ID}")
        assert resp.status_code == 410


@pytest.mark.unit
class TestCreatePost:
    @pytest.mark.asyncio
    async def test_returns_201_with_id(self, client, service):
        post_id = uuid.uuid4()
        service.get_project_info.return_value = make_project_dict(
            creator_id=USER_ID)
        service.create_post.return_value = post_id
        async with client as c:
            resp = await c.post(f"/project/{PROJECT_ID}/post", json=make_post_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 201
        assert resp.json()["id"] == str(post_id)

    @pytest.mark.asyncio
    async def test_returns_403_when_not_creator(self, client, service):
        service.get_project_info.return_value = make_project_dict(
            creator_id=USER_ID)
        async with client as c:
            resp = await c.post(f"/project/{PROJECT_ID}/post", json=make_post_payload(), headers=OTHER_USER_HEADERS)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_project_not_found(self, client, service):
        service.get_project_info.side_effect = project_errors.ProjectNotFoundError(
            "not found")
        async with client as c:
            resp = await c.post(f"/project/{PROJECT_ID}/post", json=make_post_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_project_deleted(self, client, service):
        service.get_project_info.return_value = make_project_dict(
            creator_id=USER_ID)
        service.create_post.side_effect = project_errors.ProjectDeletedError(
            "deleted")
        async with client as c:
            resp = await c.post(f"/project/{PROJECT_ID}/post", json=make_post_payload(), headers=AUTH_HEADERS)
        assert resp.status_code == 410


@pytest.mark.unit
class TestUpdatePost:
    @pytest.mark.asyncio
    async def test_returns_200_on_success(self, client, service):
        service.get_post.return_value = make_post_dict(creator_id=USER_ID)
        service.update_post.return_value = None
        async with client as c:
            resp = await c.put(f"/project/{PROJECT_ID}/post/{POST_ID}", json={"label": "Updated"}, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Post updated successfully"

    @pytest.mark.asyncio
    async def test_returns_403_when_not_creator(self, client, service):
        service.get_post.return_value = make_post_dict(creator_id=USER_ID)
        async with client as c:
            resp = await c.put(f"/project/{PROJECT_ID}/post/{POST_ID}", json={"label": "Updated"}, headers=OTHER_USER_HEADERS)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_post_not_found(self, client, service):
        service.get_post.side_effect = project_errors.PostNotFoundError(
            "not found")
        async with client as c:
            resp = await c.put(f"/project/{PROJECT_ID}/post/{POST_ID}", json={"label": "Updated"}, headers=AUTH_HEADERS)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_project_deleted(self, client, service):
        service.get_post.return_value = make_post_dict(creator_id=USER_ID)
        service.update_post.side_effect = project_errors.ProjectDeletedError(
            "deleted")
        async with client as c:
            resp = await c.put(f"/project/{PROJECT_ID}/post/{POST_ID}", json={"label": "Updated"}, headers=AUTH_HEADERS)
        assert resp.status_code == 410


@pytest.mark.unit
class TestDeletePost:
    @pytest.mark.asyncio
    async def test_returns_200_on_success(self, client, service):
        service.get_post.return_value = make_post_dict(creator_id=USER_ID)
        service.delete_post.return_value = None
        async with client as c:
            resp = await c.delete(f"/project/{PROJECT_ID}/post/{POST_ID}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Post deleted successfully"

    @pytest.mark.asyncio
    async def test_returns_403_when_not_creator(self, client, service):
        service.get_post.return_value = make_post_dict(creator_id=USER_ID)
        async with client as c:
            resp = await c.delete(f"/project/{PROJECT_ID}/post/{POST_ID}", headers=OTHER_USER_HEADERS)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_post_not_found(self, client, service):
        service.get_post.side_effect = project_errors.PostNotFoundError(
            "not found")
        async with client as c:
            resp = await c.delete(f"/project/{PROJECT_ID}/post/{POST_ID}", headers=AUTH_HEADERS)
        assert resp.status_code == 404


@pytest.mark.unit
class TestGetPost:
    @pytest.mark.asyncio
    async def test_returns_200_with_post_data(self, client, service):
        service.get_post.return_value = make_post_dict()
        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/post/{POST_ID}")
        assert resp.status_code == 200
        assert resp.json()["label"] == "Test Post"

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self, client, service):
        service.get_post.side_effect = project_errors.PostNotFoundError(
            "not found")
        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/post/{POST_ID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_project_deleted(self, client, service):
        service.get_post.side_effect = project_errors.ProjectDeletedError(
            "deleted")
        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/post/{POST_ID}")
        assert resp.status_code == 410


@pytest.mark.unit
class TestAddMember:
    @pytest.mark.asyncio
    async def test_returns_200_on_success(self, client, service):
        service.add_member.return_value = None
        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/member",
                json={"id": str(USER_ID), "name": "testuser",
                      "role": "VOLUNTEER", "avatar_link": "http://x.com/a.png"},
                headers=AUTH_HEADERS,
            )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Member added successfully"

    @pytest.mark.asyncio
    async def test_returns_403_when_adding_other_user(self, client):
        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/member",
                json={"id": str(USER_ID_2), "name": "other",
                      "role": "VOLUNTEER", "avatar_link": "http://x.com/a.png"},
                headers=AUTH_HEADERS,
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_409_when_already_member(self, client, service):
        service.add_member.side_effect = project_errors.UserAlreadyExistsError(
            "exists")
        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/member",
                json={"id": str(USER_ID), "name": "testuser",
                      "role": "VOLUNTEER", "avatar_link": "http://x.com/a.png"},
                headers=AUTH_HEADERS,
            )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_returns_404_when_project_not_found(self, client, service):
        service.add_member.side_effect = project_errors.ProjectNotFoundError(
            "not found")
        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/member",
                json={"id": str(USER_ID), "name": "testuser",
                      "role": "VOLUNTEER", "avatar_link": "http://x.com/a.png"},
                headers=AUTH_HEADERS,
            )
        assert resp.status_code == 404


@pytest.mark.unit
class TestRemoveMember:
    @pytest.mark.asyncio
    async def test_returns_200_on_success(self, client, service):
        service.remove_member.return_value = None
        async with client as c:
            resp = await c.delete(f"/project/{PROJECT_ID}/member/{USER_ID}", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Member removed successfully"

    @pytest.mark.asyncio
    async def test_returns_403_when_removing_other_user(self, client):
        async with client as c:
            resp = await c.delete(f"/project/{PROJECT_ID}/member/{USER_ID_2}", headers=AUTH_HEADERS)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_user_not_member(self, client, service):
        service.remove_member.side_effect = project_errors.UserNotFoundError(
            "not found")
        async with client as c:
            resp = await c.delete(f"/project/{PROJECT_ID}/member/{USER_ID}", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_project_deleted(self, client, service):
        service.remove_member.side_effect = project_errors.ProjectDeletedError(
            "deleted")
        async with client as c:
            resp = await c.delete(f"/project/{PROJECT_ID}/member/{USER_ID}", headers=AUTH_HEADERS)
        assert resp.status_code == 410
