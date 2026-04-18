from fastapi import APIRouter, HTTPException, Depends, status
from uuid import UUID
from typing import List
from datetime import datetime, timezone

from src.services.project_service import ProjectService
from src.api.http.dependencies import get_current_user, UserInfo
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
    async def create_project(
        project_data: ProjectCreateDTO,
        current_user: UserInfo = Depends(get_current_user)
    ):
        project = Project(
            id=None,
            label=project_data.label,
            creator_id=current_user.user_id,
            creator=current_user.username,
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
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e))

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
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e))

    @router.put("/{project_id}", response_model=dict)
    async def update_project(
        project_id: UUID,
        project_data: ProjectUpdateDTO,
        current_user: UserInfo = Depends(get_current_user)
    ):
        try:
            existing = await project_service.get_project_info(project_id)
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

        if existing.creator_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project creator can update the project"
            )

        updated_project = Project(
            id=project_id,
            label=project_data.label,
            creator_id=existing.creator_id,
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
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e))
        except project_errors.ProjectFinishedError as e:
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
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e))

    @router.post("/{project_id}/task", response_model=dict, status_code=status.HTTP_201_CREATED)
    async def create_task(
        project_id: UUID,
        task_data: TaskCreateDTO,
        current_user: UserInfo = Depends(get_current_user)
    ):
        try:
            existing = await project_service.get_project_info(project_id)
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

        if existing.creator_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project creator can create tasks"
            )

        if existing.status == ProjectStatusEnum.DELETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create tasks for a deleted project"
            )
        elif existing.status == ProjectStatusEnum.FINISHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create tasks for a finished project"
            )

        task = Task(
            task_id=None,
            project_id=project_id,
            label=task_data.label,
            creator_id=current_user.user_id,
            creator=current_user.username,
            short_description=task_data.short_description,
            description=task_data.description,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            status=TaskStatusEnum.ACTIVE,
            answers_count=0
        )

        try:
            task_id = await project_service.create_task(task)
            return {"id": task_id, "message": "Task created successfully"}
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            )
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            )
        except project_errors.ProjectFinishedError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )

    @router.patch("/{project_id}/task/{task_id}", response_model=dict)
    async def update_task(
        task_id: UUID,
        task_data: TaskUpdateDTO,
        current_user: UserInfo = Depends(get_current_user)
    ):
        try:
            existing = await project_service.get_task(task_id)
        except project_errors.TaskNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )

        if existing.creator_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project creator can create tasks"
            )

        task = Task(
            task_id=task_id,
            project_id=existing.project_id,
            label=task_data.label if task_data.label else existing.label,
            creator_id=existing.creator_id,
            creator=existing.creator,
            short_description=task_data.short_description if task_data.short_description else existing.short_description,
            description=task_data.description if task_data.description else existing.description,
            created_at=existing.created_at,
            updated_at=datetime.now(timezone.utc),
            status=TaskStatusEnum(
                task_data.status) if task_data.status else existing.status,
            answers_count=existing.answers_count
        )

        try:
            await project_service.update_task(task)
            return {"message": "Task updated successfully"}
        except project_errors.TaskNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            )
        except project_errors.ProjectFinishedError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )

    @router.get("/{project_id}/task/{task_id}", response_model=TaskDTO)
    async def get_task(task_id: UUID):
        try:
            task = await project_service.get_task(task_id)
            return TaskDTO(
                task_id=task.task_id,
                project_id=task.project_id,
                label=task.label,
                creator_id=task.creator_id,
                creator=task.creator,
                short_description=task.short_description,
                description=task.description,
                created_at=task.created_at,
                updated_at=task.updated_at,
                status=task.status,
                answers_count=task.answers_count
            )
        except project_errors.TaskNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            )

    @router.post("/{project_id}/post", response_model=dict, status_code=status.HTTP_201_CREATED)
    async def create_post(
        project_id: UUID,
        post_data: PostCreateDTO,
        current_user: UserInfo = Depends(get_current_user)
    ):
        try:
            existing = await project_service.get_project_info(project_id)
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )

        if existing.creator_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project creator can create posts"
            )

        post = Post(
            post_id=None,
            project_id=project_id,
            label=post_data.label,
            creator=post_data.creator,
            short_description=post_data.short_description,
            description=post_data.description,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        try:
            post_id = await project_service.create_post(post)
            return {"id": post_id, "message": "Post created successfully"}
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            )
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            )
        except project_errors.ProjectFinishedError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )

    @router.put("/{project_id}/post/{post_id}", response_model=dict)
    async def update_post(
        post_id: UUID,
        post_data: PostUpdateDTO,
        current_user: UserInfo = Depends(get_current_user)
    ):
        try:
            existing = await project_service.get_post(post_id)
        except project_errors.PostNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )

        if existing.creator_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the post creator can update the post"
            )

        post = Post(
            post_id=post_id,
            project_id=existing.project_id,
            label=post_data.label if post_data.label else existing.label,
            creator=existing.creator,
            short_description=post_data.short_description if post_data.short_description else existing.short_description,
            description=post_data.description if post_data.description else existing.description,
            created_at=existing.created_at,
            updated_at=datetime.now(timezone.utc)
        )

        try:
            await project_service.update_post(post)
            return {"message": "Post updated successfully"}
        except project_errors.PostNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            )
        except project_errors.ProjectFinishedError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )

    @router.delete("/{project_id}/post/{post_id}")
    async def delete_post(
        post_id: UUID,
        current_user: UserInfo = Depends(get_current_user)
    ):
        try:
            existing = await project_service.get_post(post_id)
        except project_errors.PostNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )

        if existing.creator_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the post creator can delete the post"
            )

        try:
            await project_service.delete_post(post_id)
            return {"message": "Post deleted successfully"}
        except project_errors.PostNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )

    @router.get("/{project_id}/post/{post_id}", response_model=PostDTO)
    async def get_post(post_id: UUID):
        try:
            post = await project_service.get_post(post_id)
            return PostDTO(
                post_id=post.post_id,
                project_id=post.project_id,
                label=post.label,
                creator=post.creator,
                short_description=post.short_description,
                description=post.description,
                created_at=post.created_at,
                updated_at=post.updated_at
            )
        except project_errors.PostNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            )

    @router.post("/{project_id}/member")
    async def add_member(
        project_id: UUID,
        user_data: DenormUserDTO,
        current_user: UserInfo = Depends(get_current_user)
    ):
        if user_data.id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Users can only add themselves as members to a project"
            )

        try:
            await project_service.add_member(project_id, user_data.user_id)
            return {"message": "Member added successfully"}
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except project_errors.UserAlreadyExistsError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            )
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            )
        except project_errors.ProjectFinishedError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )

    @router.delete("/{project_id}/member/{user_id}")
    async def remove_member(
        project_id: UUID,
        user_id: UUID,
        current_user: UserInfo = Depends(get_current_user)
    ):
        if user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Users can only remove themselves from a project"
            )

        try:
            await project_service.remove_member(project_id, user_id)
            return {"message": "Member removed successfully"}
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except project_errors.UserNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e)
            )
        except project_errors.ProjectFinishedError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )

    return router
