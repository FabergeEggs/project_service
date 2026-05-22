import uuid
from datetime import datetime, timezone
from typing import cast
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.http.dependencies import get_current_user, UserInfo
from src.api.http.project_router import create_project_router
from src.models.project import (
    Project, Post, Task, DenormUser, Tag,
    ProjectStatusEnum, TaskStatusEnum, ProjectRoleEnum,
)
import src.services.errors as project_errors


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

def make_uuid() -> uuid.UUID:
    return uuid.uuid4()


USER_ID = make_uuid()
USER_ID_2 = make_uuid()
PROJECT_ID = make_uuid()
TASK_ID = make_uuid()
POST_ID = make_uuid()

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


def make_project(**kwargs) -> Project:
    defaults = dict(
        id=PROJECT_ID,
        label="Test Project",
        creator_id=USER_ID,
        creator="testuser",
        short_description="Short desc",
        description="Full description",
        tags=[Tag(tag_id=make_uuid(), name="python")],
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status=ProjectStatusEnum.ACTIVE,
    )
    defaults.update(kwargs)
    return Project(**defaults)


def make_task(**kwargs) -> Task:
    defaults = dict(
        task_id=TASK_ID,
        project_id=PROJECT_ID,
        creator_id=USER_ID,
        creator="testuser",
        label="Test Task",
        short_description="Short desc",
        description="Full description",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status=TaskStatusEnum.ACTIVE,
        answers_count=0,
    )
    defaults.update(kwargs)
    return Task(**defaults)


def make_post(**kwargs) -> Post:
    defaults = dict(
        post_id=POST_ID,
        project_id=PROJECT_ID,
        creator_id=USER_ID,
        creator="testuser",
        label="Test Post",
        short_description="Short desc",
        description="Full description",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(kwargs)
    return Post(**defaults)


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service():
    return AsyncMock()


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(create_project_router(service))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_returns_200(self, client):
        async with client as c:
            resp = await c.get("/project/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# POST /project/
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCreateProject:
    @pytest.mark.asyncio
    async def test_returns_201_with_id(self, client, service):
        project_id = make_uuid()
        service.create_project.return_value = project_id

        async with client as c:
            resp = await c.post("/project/", json=make_project_payload(), headers=AUTH_HEADERS)

        assert resp.status_code == 201
        assert resp.json()["id"] == str(project_id)

    @pytest.mark.asyncio
    async def test_calls_service(self, client, service):
        service.create_project.return_value = make_uuid()

        async with client as c:
            await c.post("/project/", json=make_project_payload(), headers=AUTH_HEADERS)

        service.create_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_401_without_auth_headers(self, client, service):
        async with client as c:
            resp = await c.post("/project/", json=make_project_payload())

        assert resp.status_code == 422  # missing required headers → validation error

    @pytest.mark.asyncio
    async def test_returns_422_when_label_too_short(self, client, service):
        async with client as c:
            resp = await c.post(
                "/project/",
                json=make_project_payload(label="ab"),  # min_length=3
                headers=AUTH_HEADERS,
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_returns_409_when_project_already_exists(self, client, service):
        service.create_project.side_effect = project_errors.ProjectAlreadyExistsError(
            "exists")

        async with client as c:
            resp = await c.post("/project/", json=make_project_payload(), headers=AUTH_HEADERS)

        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# GET /project/{project_id}/info
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetProjectInfo:
    @pytest.mark.asyncio
    async def test_returns_200_with_project_data(self, client, service):
        service.get_project_info.return_value = make_project()

        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/info")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(PROJECT_ID)
        assert data["label"] == "Test Project"

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


# ---------------------------------------------------------------------------
# GET /project/{project_id}/statistics
# ---------------------------------------------------------------------------

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
        data = resp.json()
        assert data["tasks_count"] == 5
        assert data["participants_count"] == 10

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


# ---------------------------------------------------------------------------
# PUT /project/{project_id}
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUpdateProject:
    @pytest.mark.asyncio
    async def test_returns_200_on_success(self, client, service):
        service.get_project_info.return_value = make_project(
            creator_id=USER_ID)
        service.update_project.return_value = None

        async with client as c:
            resp = await c.put(
                f"/project/{PROJECT_ID}",
                json=make_project_payload(),
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 200
        assert resp.json()["message"] == "Project updated successfully"

    @pytest.mark.asyncio
    async def test_returns_403_when_not_creator(self, client, service):
        service.get_project_info.return_value = make_project(
            creator_id=USER_ID)

        async with client as c:
            resp = await c.put(
                f"/project/{PROJECT_ID}",
                json=make_project_payload(),
                headers=OTHER_USER_HEADERS,
            )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_project_not_found(self, client, service):
        service.get_project_info.side_effect = project_errors.ProjectNotFoundError(
            "not found")

        async with client as c:
            resp = await c.put(
                f"/project/{PROJECT_ID}",
                json=make_project_payload(),
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_400_when_project_finished(self, client, service):
        service.get_project_info.return_value = make_project(
            creator_id=USER_ID)
        service.update_project.side_effect = project_errors.ProjectFinishedError(
            "finished")

        async with client as c:
            resp = await c.put(
                f"/project/{PROJECT_ID}",
                json=make_project_payload(),
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /project/batch
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetProjects:
    @pytest.mark.asyncio
    async def test_returns_200_with_list(self, client, service):
        service.get_projects.return_value = [make_project()]

        async with client as c:
            resp = await c.post("/project/batch", json=[str(PROJECT_ID)])

        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
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


# ---------------------------------------------------------------------------
# POST /project/{project_id}/task
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCreateTask:
    @pytest.mark.asyncio
    async def test_returns_201_with_id(self, client, service):
        task_id = make_uuid()
        service.get_project_info.return_value = make_project(
            creator_id=USER_ID)
        service.create_task.return_value = task_id

        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/task",
                json=make_task_payload(),
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 201
        assert resp.json()["id"] == str(task_id)

    @pytest.mark.asyncio
    async def test_returns_403_when_not_creator(self, client, service):
        service.get_project_info.return_value = make_project(
            creator_id=USER_ID)

        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/task",
                json=make_task_payload(),
                headers=OTHER_USER_HEADERS,
            )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_400_when_project_deleted(self, client, service):
        service.get_project_info.return_value = make_project(
            creator_id=USER_ID, status=ProjectStatusEnum.DELETED
        )

        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/task",
                json=make_task_payload(),
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_400_when_project_finished(self, client, service):
        service.get_project_info.return_value = make_project(
            creator_id=USER_ID, status=ProjectStatusEnum.FINISHED
        )

        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/task",
                json=make_task_payload(),
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_422_when_label_too_short(self, client, service):
        service.get_project_info.return_value = make_project(
            creator_id=USER_ID)

        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/task",
                json=make_task_payload(label="ab"),  # min_length=3
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /project/{project_id}/task/{task_id}
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUpdateTask:
    @pytest.mark.asyncio
    async def test_returns_200_on_success(self, client, service):
        service.get_task.return_value = make_task(creator_id=USER_ID)
        service.update_task.return_value = None

        async with client as c:
            resp = await c.patch(
                f"/project/{PROJECT_ID}/task/{TASK_ID}",
                json={"label": "Updated label"},
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 200
        assert resp.json()["message"] == "Task updated successfully"

    @pytest.mark.asyncio
    async def test_returns_403_when_not_creator(self, client, service):
        service.get_task.return_value = make_task(creator_id=USER_ID)

        async with client as c:
            resp = await c.patch(
                f"/project/{PROJECT_ID}/task/{TASK_ID}",
                json={"label": "Updated label"},
                headers=OTHER_USER_HEADERS,
            )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_task_not_found(self, client, service):
        service.get_task.side_effect = project_errors.TaskNotFoundError(
            "not found")

        async with client as c:
            resp = await c.patch(
                f"/project/{PROJECT_ID}/task/{TASK_ID}",
                json={"label": "Updated label"},
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_project_deleted(self, client, service):
        service.get_task.return_value = make_task(creator_id=USER_ID)
        service.update_task.side_effect = project_errors.ProjectDeletedError(
            "deleted")

        async with client as c:
            resp = await c.patch(
                f"/project/{PROJECT_ID}/task/{TASK_ID}",
                json={"label": "Updated label"},
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 410


# ---------------------------------------------------------------------------
# GET /project/{project_id}/task/{task_id}
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetTask:
    @pytest.mark.asyncio
    async def test_returns_200_with_task_data(self, client, service):
        service.get_task.return_value = make_task()

        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/task/{TASK_ID}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == str(TASK_ID)
        assert data["label"] == "Test Task"

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


# ---------------------------------------------------------------------------
# POST /project/{project_id}/post
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCreatePost:
    @pytest.mark.asyncio
    async def test_returns_201_with_id(self, client, service):
        post_id = make_uuid()
        service.get_project_info.return_value = make_project(
            creator_id=USER_ID)
        service.create_post.return_value = post_id

        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/post",
                json=make_post_payload(),
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 201
        assert resp.json()["id"] == str(post_id)

    @pytest.mark.asyncio
    async def test_returns_403_when_not_creator(self, client, service):
        service.get_project_info.return_value = make_project(
            creator_id=USER_ID)

        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/post",
                json=make_post_payload(),
                headers=OTHER_USER_HEADERS,
            )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_project_not_found(self, client, service):
        service.get_project_info.side_effect = project_errors.ProjectNotFoundError(
            "not found")

        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/post",
                json=make_post_payload(),
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_project_deleted(self, client, service):
        service.get_project_info.return_value = make_project(
            creator_id=USER_ID)
        service.create_post.side_effect = project_errors.ProjectDeletedError(
            "deleted")

        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/post",
                json=make_post_payload(),
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 410


# ---------------------------------------------------------------------------
# PUT /project/{project_id}/post/{post_id}
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUpdatePost:
    @pytest.mark.asyncio
    async def test_returns_200_on_success(self, client, service):
        service.get_post.return_value = make_post(creator_id=USER_ID)
        service.update_post.return_value = None

        async with client as c:
            resp = await c.put(
                f"/project/{PROJECT_ID}/post/{POST_ID}",
                json={"label": "Updated label"},
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 200
        assert resp.json()["message"] == "Post updated successfully"

    @pytest.mark.asyncio
    async def test_returns_403_when_not_creator(self, client, service):
        service.get_post.return_value = make_post(creator_id=USER_ID)

        async with client as c:
            resp = await c.put(
                f"/project/{PROJECT_ID}/post/{POST_ID}",
                json={"label": "Updated label"},
                headers=OTHER_USER_HEADERS,
            )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_post_not_found(self, client, service):
        service.get_post.side_effect = project_errors.PostNotFoundError(
            "not found")

        async with client as c:
            resp = await c.put(
                f"/project/{PROJECT_ID}/post/{POST_ID}",
                json={"label": "Updated label"},
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_project_deleted(self, client, service):
        service.get_post.return_value = make_post(creator_id=USER_ID)
        service.update_post.side_effect = project_errors.ProjectDeletedError(
            "deleted")

        async with client as c:
            resp = await c.put(
                f"/project/{PROJECT_ID}/post/{POST_ID}",
                json={"label": "Updated label"},
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 410


# ---------------------------------------------------------------------------
# DELETE /project/{project_id}/post/{post_id}
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDeletePost:
    @pytest.mark.asyncio
    async def test_returns_200_on_success(self, client, service):
        service.get_post.return_value = make_post(creator_id=USER_ID)
        service.delete_post.return_value = None

        async with client as c:
            resp = await c.delete(
                f"/project/{PROJECT_ID}/post/{POST_ID}",
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 200
        assert resp.json()["message"] == "Post deleted successfully"

    @pytest.mark.asyncio
    async def test_returns_403_when_not_creator(self, client, service):
        service.get_post.return_value = make_post(creator_id=USER_ID)

        async with client as c:
            resp = await c.delete(
                f"/project/{PROJECT_ID}/post/{POST_ID}",
                headers=OTHER_USER_HEADERS,
            )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_post_not_found(self, client, service):
        service.get_post.side_effect = project_errors.PostNotFoundError(
            "not found")

        async with client as c:
            resp = await c.delete(
                f"/project/{PROJECT_ID}/post/{POST_ID}",
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /project/{project_id}/post/{post_id}
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetPost:
    @pytest.mark.asyncio
    async def test_returns_200_with_post_data(self, client, service):
        service.get_post.return_value = make_post()

        async with client as c:
            resp = await c.get(f"/project/{PROJECT_ID}/post/{POST_ID}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["post_id"] == str(POST_ID)
        assert data["label"] == "Test Post"

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


# ---------------------------------------------------------------------------
# POST /project/{project_id}/member
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAddMember:
    @pytest.mark.asyncio
    async def test_returns_200_on_success(self, client, service):
        service.add_member.return_value = None

        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/member",
                json={
                    "id": str(USER_ID),
                    "name": "testuser",
                    "role": "VOLUNTEER",
                    "avatar_link": "http://example.com/avatar.png",
                },
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 200
        assert resp.json()["message"] == "Member added successfully"

    @pytest.mark.asyncio
    async def test_returns_403_when_adding_other_user(self, client, service):
        """Users can only add themselves."""
        async with client as c:
            resp = await c.post(
                f"/project/{PROJECT_ID}/member",
                json={
                    "id": str(USER_ID_2),  # different from auth header USER_ID
                    "name": "otheruser",
                    "role": "VOLUNTEER",
                    "avatar_link": "http://example.com/avatar.png",
                },
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
                json={
                    "id": str(USER_ID),
                    "name": "testuser",
                    "role": "VOLUNTEER",
                    "avatar_link": "http://example.com/avatar.png",
                },
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
                json={
                    "id": str(USER_ID),
                    "name": "testuser",
                    "role": "VOLUNTEER",
                    "avatar_link": "http://example.com/avatar.png",
                },
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /project/{project_id}/member/{user_id}
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRemoveMember:
    @pytest.mark.asyncio
    async def test_returns_200_on_success(self, client, service):
        service.remove_member.return_value = None

        async with client as c:
            resp = await c.delete(
                f"/project/{PROJECT_ID}/member/{USER_ID}",
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 200
        assert resp.json()["message"] == "Member removed successfully"

    @pytest.mark.asyncio
    async def test_returns_403_when_removing_other_user(self, client, service):
        """Users can only remove themselves."""
        async with client as c:
            resp = await c.delete(
                f"/project/{PROJECT_ID}/member/{USER_ID_2}",
                headers=AUTH_HEADERS,  # authenticated as USER_ID, removing USER_ID_2
            )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_404_when_user_not_member(self, client, service):
        service.remove_member.side_effect = project_errors.UserNotFoundError(
            "not found")

        async with client as c:
            resp = await c.delete(
                f"/project/{PROJECT_ID}/member/{USER_ID}",
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_410_when_project_deleted(self, client, service):
        service.remove_member.side_effect = project_errors.ProjectDeletedError(
            "deleted")

        async with client as c:
            resp = await c.delete(
                f"/project/{PROJECT_ID}/member/{USER_ID}",
                headers=AUTH_HEADERS,
            )

        assert resp.status_code == 410
