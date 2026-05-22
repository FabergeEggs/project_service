import pytest
import src.services.errors as project_errors

from uuid import uuid4


@pytest.mark.integration
class TestCreateProjectAPI:

    @pytest.mark.asyncio
    async def test_create_project_success(self, client, repo, kafka, auth_header):
        project_id = uuid4()
        repo.create_project.return_value = project_id

        response = await client.post(
            "/project/",
            json={
                "label": "Test Project",
                "short_description": "Short description",
                "description": "Full description",
                "tags": ["python", "testing"],
                "status": "ACTIVE"
            },
            headers=auth_header
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == str(project_id)
        assert data["message"] == "Project created successfully"

        repo.create_project.assert_awaited_once()
        kafka.send_create_project.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_project_invalid_data(self, client, repo, auth_header):
        response = await client.post(
            "/project/",
            json={
                "label": "A" * 300,
                "short_description": "",
                "description": "",
                "tags": [],
                "status": "INVALID"
            },
            headers=auth_header
        )

        assert response.status_code == 400
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_create_project_unauthorized(self, client):
        response = await client.post(
            "/project/",
            json={
                "label": "Test Project",
                "short_description": "Short",
                "description": "Full",
                "tags": [],
                "status": "ACTIVE"
            }
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_project_already_exists(self, client, repo, auth_header):
        repo.create_project.side_effect = project_errors.ProjectAlreadyExistsError()

        response = await client.post(
            "/project/",
            json={
                "label": "Duplicate Project",
                "short_description": "Short",
                "description": "Full",
                "tags": [],
                "status": "ACTIVE"
            },
            headers=auth_header
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


@pytest.mark.integration
class TestGetProjectAPI:

    @pytest.mark.asyncio
    async def test_get_project_success(self, client, repo, auth_header):
        """API: получение информации о проекте"""
        project_id = uuid4()
        repo.get_project_info.return_value = {
            "id": str(project_id),
            "label": "Test Project",
            "description": "Full description",
            "creator_id": "123e4567-e89b-12d3-a456-426614174000",
            "creator_name": "Test User",
            "status": "ACTIVE",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "tags": []
        }

        response = await client.get(
            f"/project/{project_id}/info",
            headers=auth_header
        )

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == str(project_id)
        assert data["label"] == "Test Project"

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client, repo, auth_header):
        """API: проект не найден"""
        project_id = uuid4()
        repo.get_project_info.side_effect = project_errors.ProjectNotFoundError()

        response = await client.get(
            f"/project/{project_id}/info",
            headers=auth_header
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_deleted(self, client, repo, auth_header):
        """API: проект удалён"""
        project_id = uuid4()
        repo.get_project_info.side_effect = project_errors.ProjectDeletedError()

        response = await client.get(
            f"/project/{project_id}/info",
            headers=auth_header
        )

        assert response.status_code == 410  # Gone
