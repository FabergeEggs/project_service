from fastapi import APIRouter
from src.services.project_service import ProjectService


def create_project_router(project_service: ProjectService) -> APIRouter:
    router = APIRouter(prefix="/project", tags=["project"])

    @router.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "project-service"}

    return router
