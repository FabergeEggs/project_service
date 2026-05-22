# tests/integration/conftest.py
import pytest
from unittest.mock import AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient
from uuid import uuid4

from src.api.http.project_router import create_project_router
from src.services.project_service import ProjectService


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def kafka():
    return AsyncMock()


@pytest.fixture
def project_service(repo, kafka):
    return ProjectService(
        project_repository=repo,
        kafka_producer=kafka
    )
    return ProjectService(
        project_repository=repo,
        kafka_producer=kafka
    )


@pytest.fixture
def app(repo, kafka) -> FastAPI:
    project_service = ProjectService(
        project_repository=repo,
        kafka_producer=kafka
    )
    router = create_project_router(project_service)

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_header():
    return {
        "X-User-Id": str(uuid4()),
        "X-User-Name": "Test User",
        "X-User-Roles": "user"
    }
