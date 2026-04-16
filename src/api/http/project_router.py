from fastapi import APIRouter, HTTPException, status
from uuid import UUID
from typing import List
from datetime import datetime, timezone

from src.services.project_service import ProjectService
from src.models.project import (
    Project, Post, Task, DenormUser, Tag,
    ProjectStatusEnum, TaskStatusEnum, ProjectRoleEnum
)
from src.api.http.dto import (
    ProjectDTO, ProjectInfoDTO, ProjectDetailDTO, ProjectCreateDTO, ProjectUpdateDTO,
    ProjectStatsDTO, TaskDTO, TaskCreateDTO, TaskUpdateDTO,
    PostDTO, PostCreateDTO, PostUpdateDTO, TagDTO, DenormUserDTO
)
import src.services.errors as project_errors


def create_project_router(project_service: ProjectService) -> APIRouter:
    router = APIRouter(prefix="/project", tags=["project"])

    @router.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "project-service"}

    @router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
    async def create_project(project_data: ProjectCreateDTO):
        project = Project(
            id=None,
            label=project_data.label,
            creator=project_data.creator,
            short_description=project_data.short_description,
            description=project_data.description,
            tags=[
                Tag(tag_id=None, name=tag_name)
                for tag_name in project_data.tags
            ],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            status=ProjectStatusEnum.ACTIVE
        )

        try:
            project_id = await project_service.create_project(project)
            return {"id": project_id, "message": "Project created successfully"}
        except project_errors.ProjectAlreadyExistsError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.get("/{project_id}/info", response_model=ProjectDTO)
    async def get_project_info(project_id: UUID):
        try:
            project = await project_service.get_project_info(project_id)
            return ProjectDTO(
                id=project.id,
                label=project.label,
                creator=project.creator,
                short_description=project.short_description,
                description=project.description,
                tags=[
                    TagDTO(tag_id=tag.tag_id, name=tag.name)
                    for tag in project.tags
                ],
                created_at=project.created_at,
                updated_at=project.updated_at,
                status=project.status
            )
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @router.get("/{project_id}/statistics", response_model=ProjectStatsDTO)
    async def get_project_statistics(project_id: UUID):
        try:
            stats = await project_service.get_project_statistics(project_id)
            return ProjectStatsDTO(
                project_id=stats["project_id"],
                tasks_count=stats["tasks_count"],
                participants_count=stats["members_count"],
                answers_count=stats["answers_count"]
            )
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @router.put("/{project_id}", response_model=dict)
    async def update_project(project_id: UUID, project_data: ProjectUpdateDTO):
        try:
            existing = await project_service.get_project_info(project_id)
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

        updated_project = Project(
            id=project_id,
            label=project_data.label,
            creator=existing.creator,
            short_description=project_data.short_description,
            description=project_data.description,
            tags=[
                Tag(tag_id=None, name=tag_name)
                for tag_name in project_data.tags
            ],
            created_at=existing.created_at,
            updated_at=datetime.now(timezone.utc),
            status=project_data.status
        )

        try:
            await project_service.update_project(updated_project)
            return {"message": "Project updated successfully"}
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/batch", response_model=List[ProjectDTO])
    async def get_projects(project_ids: List[UUID]):
        try:
            projects = await project_service.get_projects(project_ids)
            return [
                ProjectDTO(
                    id=project.id,
                    label=project.label,
                    creator=project.creator,
                    short_description=project.short_description,
                    description=project.description,
                    tags=[
                        TagDTO(tag_id=tag.tag_id, name=tag.name)
                        for tag in project.tags
                    ],
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                    status=project.status
                ) for project in projects
            ]
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return router
