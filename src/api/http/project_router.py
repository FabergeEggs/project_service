from fastapi import APIRouter, HTTPException, Depends, status
from uuid import UUID
from typing import Optional
from datetime import datetime, timezone

from src.services.project_service import ProjectService
from src.api.http.dependencies import get_current_user, UserInfo
from src.models.project import (
    Project, Post, Task, Tag, DenormUser,
    ProjectStatusEnum, TaskStatusEnum
)
from src.api.http.dto import (
    ProjectDTO, ProjectInfoDTO, ProjectCreateDTO, ProjectUpdateDTO,
    ProjectStatsDTO, TaskDTO, TaskCreateDTO, TaskUpdateDTO,
    PostDTO, PostCreateDTO, PostUpdateDTO, TagDTO, DenormUserDTO, PublicationDTO,
    PublicationsResponse, MembershipProjectDTO, MembershipsDTO
)
import src.services.errors as project_errors


def create_project_router(project_service: ProjectService) -> APIRouter:
    """
    Create and configure the project router with all endpoints.

    Args:
        project_service: Service instance for project business logic.

    Returns:
        Configured APIRouter with all project endpoints.
    """
    router = APIRouter(prefix="/project", tags=["project"])

    @router.get("/health")
    async def health_check():
        """
        Health check endpoint for service monitoring.

        Returns:
            Dictionary with service status and name.
        """
        return {"status": "healthy", "service": "project-service"}

    @router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
    async def create_project(
        project_data: ProjectCreateDTO,
        current_user: UserInfo = Depends(get_current_user)
    ) -> dict:
        """
        Create a new project.

        Args:
            project_data: Project creation data (label, description, tags).
            current_user: Authenticated user info from JWT token.

        Returns:
            Dictionary with created project ID and success message.

        Raises:
            HTTPException 409: If project already exists.
            HTTPException 400: For other errors during creation.
        """
        project = Project(
            id=None,
            label=project_data.label,
            creator_id=current_user.user_id,
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

    @router.get("/{project_id}/info", response_model=ProjectInfoDTO)
    async def get_project_info(project_id: UUID) -> ProjectInfoDTO:
        """
        Get detailed information about a specific project.

        Args:
            project_id: UUID of the project to retrieve.

        Returns:
            ProjectInfoDTO with project details including tags and creator.

        Raises:
            HTTPException 404: If project not found.
            HTTPException 410: If project is deleted.
        """
        try:
            project = await project_service.get_project_info(project_id)

            return ProjectInfoDTO(
                project_id=project["id"],
                label=project["label"],
                creator_id=project["creator_id"],
                creator=project["creator_name"],
                description=project["description"],
                tags=[
                    TagDTO(
                        tag_id=tag.tag_id,
                        name=tag.name
                    )
                    for tag in project["tags"]
                ],
                created_at=project["created_at"],
                status=project["status"]
            )
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e))

    @router.get("/{project_id}/statistics", response_model=ProjectStatsDTO)
    async def get_project_statistics(project_id: UUID):
        """
        Get aggregated statistics for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            ProjectStatsDTO with tasks, participants, and answers counts.

        Raises:
            HTTPException 404: If project not found.
            HTTPException 410: If project is deleted.
        """
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
        """
        Update an existing project.

        Args:
            project_id: UUID of the project to update.
            project_data: Updated project data.
            current_user: Authenticated user info.

        Returns:
            Dictionary with success message.

        Raises:
            HTTPException 404: If project not found.
            HTTPException 403: If user is not the project creator.
            HTTPException 410: If project is deleted.
            HTTPException 400: If project is finished.
        """
        try:
            existing = await project_service.get_project_info(project_id)
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

        if existing["creator_id"] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project creator can update the project"
            )

        updated_project = Project(
            id=project_id,
            label=project_data.label,
            creator_id=existing["creator_id"],
            short_description=project_data.short_description,
            description=project_data.description,
            tags=[
                Tag(tag_id=None, name=tag_name)
                for tag_name in project_data.tags
            ],
            created_at=existing["created_at"],
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

    @router.post("/batch", response_model=list[ProjectDTO])
    async def get_projects(project_ids: list[UUID]):
        """
        Retrieve multiple projects by their IDs.

        Args:
            project_ids: List of project UUIDs to fetch.

        Returns:
            List of ProjectDTO objects with project details.

        Raises:
            HTTPException 404: If any project not found.
            HTTPException 410: If any project is deleted.
        """
        try:
            projects = await project_service.get_projects(project_ids)
            return [
                ProjectDTO(
                    id=project["id"],
                    label=project["label"],
                    creator_id=project["creator_id"],
                    creator=project["creator"],
                    short_description=project["short_description"],
                    description=project["description"],
                    tags=[
                        TagDTO(tag_id=tag.tag_id, name=tag.name)
                        for tag in project["tags"]
                    ],
                    created_at=project["created_at"],
                    updated_at=project["updated_at"],
                    status=project["status"]
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
        """
        Create a new task within a project.

        Args:
            project_id: UUID of the parent project.
            task_data: Task creation data.
            current_user: Authenticated user info.

        Returns:
            Dictionary with created task ID and success message.

        Raises:
            HTTPException 404: If project not found.
            HTTPException 403: If user is not the project creator.
            HTTPException 410: If project is deleted.
            HTTPException 400: If project is finished.
        """
        try:
            existing = await project_service.get_project_info(project_id)
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e))

        if existing["creator_id"] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project creator can create tasks"
            )

        task = Task(
            task_id=None,
            project_id=project_id,
            creator_id=current_user.user_id,
            label=task_data.label,
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
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except project_errors.ProjectDeletedError as e:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail=str(e))
        except project_errors.ProjectFinishedError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.put("/{project_id}/task/{task_id}", response_model=dict)
    async def update_task(
        task_id: UUID,
        task_data: TaskUpdateDTO,
        current_user: UserInfo = Depends(get_current_user)
    ):
        """
        Update an existing task.

        Args:
            task_id: UUID of the task to update.
            task_data: Updated task data.
            current_user: Authenticated user info.

        Returns:
            Dictionary with success message.

        Raises:
            HTTPException 404: If task or project not found.
            HTTPException 403: If user is not the task creator.
            HTTPException 410: If project is deleted.
            HTTPException 400: If project is finished.
        """
        try:
            existing = await project_service.get_task(task_id)
        except project_errors.TaskNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )

        if existing["creator_id"] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project creator can create tasks"
            )

        task = Task(
            task_id=task_id,
            project_id=existing["project_id"],
            label=task_data.label,
            creator_id=existing["creator_id"],
            short_description=task_data.short_description,
            description=task_data.description,
            created_at=existing["created_at"],
            updated_at=datetime.now(timezone.utc),
            status=TaskStatusEnum(task_data.status),
            answers_count=existing["answers_count"]
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
        """
        Get detailed information about a specific task.

        Args:
            task_id: UUID of the task to retrieve.

        Returns:
            TaskDTO with task details including creator.

        Raises:
            HTTPException 404: If task or project not found.
            HTTPException 410: If project is deleted.
        """
        try:
            task = await project_service.get_task(task_id)
            return TaskDTO(
                task_id=task["task_id"],
                project_id=task["project_id"],
                label=task["label"],
                creator_id=task["creator_id"],
                creator=task["creator_name"],
                short_description=task["short_description"],
                description=task["description"],
                created_at=task["created_at"],
                updated_at=task["updated_at"],
                status=task["status"],
                answers_count=task["answers_count"]
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
        """
        Create a new post within a project.

        Args:
            project_id: UUID of the parent project.
            post_data: Post creation data.
            current_user: Authenticated user info.

        Returns:
            Dictionary with created post ID and success message.

        Raises:
            HTTPException 404: If project not found.
            HTTPException 403: If user is not the project creator.
            HTTPException 410: If project is deleted.
            HTTPException 400: If project is finished.
        """
        try:
            existing = await project_service.get_project_info(project_id)
        except project_errors.ProjectNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )

        if existing["creator_id"] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project creator can create posts"
            )

        post = Post(
            post_id=None,
            project_id=project_id,
            creator_id=current_user.user_id,
            creator=current_user.username,
            label=post_data.label,
            short_description=post_data.short_description,
            description=post_data.description,
            comments_count=0,
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
        """
        Update an existing post.

        Args:
            post_id: UUID of the post to update.
            post_data: Updated post data.
            current_user: Authenticated user info.

        Returns:
            Dictionary with success message.

        Raises:
            HTTPException 404: If post or project not found.
            HTTPException 403: If user is not the post creator.
            HTTPException 410: If project is deleted.
            HTTPException 400: If project is finished.
        """
        try:
            existing = await project_service.get_post(post_id)
        except project_errors.PostNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )

        if existing["creator_id"] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the post creator can update the post"
            )

        post = Post(
            post_id=post_id,
            project_id=existing["project_id"],
            label=post_data.label,
            creator=existing["creator"],
            creator_id=existing["creator_id"],
            short_description=post_data.short_description,
            description=post_data.description,
            comments_count=existing["comments_count"],
            created_at=existing["created_at"],
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
        """
        Delete a post.

        Args:
            post_id: UUID of the post to delete.
            current_user: Authenticated user info.

        Returns:
            Dictionary with success message.

        Raises:
            HTTPException 404: If post not found.
            HTTPException 403: If user is not the post creator.
        """
        try:
            existing = await project_service.get_post(post_id)
        except project_errors.PostNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            )

        if existing["creator_id"] != current_user.user_id:
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
        """
        Get detailed information about a specific post.

        Args:
            post_id: UUID of the post to retrieve.

        Returns:
            PostDTO with post details including creator.

        Raises:
            HTTPException 404: If post or project not found.
            HTTPException 410: If project is deleted.
        """
        try:
            post = await project_service.get_post(post_id)
            return PostDTO(
                post_id=post["post_id"],
                project_id=post["project_id"],
                label=post["label"],
                creator_id=post["creator_id"],
                creator=post["creator_name"],
                short_description=post["short_description"],
                description=post["description"],
                comments_count=post["comments_count"],
                created_at=post["created_at"],
                updated_at=post["updated_at"]
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
        """
        Add a user as a member to a project.

        Users can only add themselves to projects.

        Args:
            project_id: UUID of the project.
            user_data: User data including role and profile info.
            current_user: Authenticated user info.

        Returns:
            Dictionary with success message.

        Raises:
            HTTPException 403: If user tries to add someone else.
            HTTPException 404: If project not found.
            HTTPException 409: If user already a member.
            HTTPException 410: If project is deleted.
            HTTPException 400: If project is finished.
        """
        if user_data.id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Users can only add themselves as members to a project"
            )

        user = DenormUser(
            id=user_data.id,
            role=user_data.role,
            name=user_data.name,
            avatar_link=user_data.avatar_link
        )

        try:
            await project_service.add_member(project_id, user)
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
    ) -> dict:
        """
        Remove a user from a project membership.

        Users can only remove themselves from projects.

        Args:
            project_id: UUID of the project.
            user_id: UUID of the user to remove.
            current_user: Authenticated user info.

        Returns:
            Dictionary with success message.

        Raises:
            HTTPException 403: If user tries to remove someone else.
            HTTPException 404: If project or user not found.
            HTTPException 410: If project is deleted.
            HTTPException 400: If project is finished.
        """
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

    @router.get("/{project_id}/publications", response_model=PublicationsResponse)
    async def get_publications(
        project_id: UUID,
        limit: int = 20,
        cursor: Optional[str] = None
    ):
        """
        Get paginated list of publications (posts and tasks) for a project.

        Supports cursor-based pagination using ISO format datetime strings.

        Args:
            project_id: UUID of the project.
            limit: Maximum number of items to return (default: 20).
            cursor: Optional cursor string (ISO datetime) for pagination.

        Returns:
            PublicationsResponse with items list, next cursor, and has_more flag.

        Raises:
            HTTPException 404: If project not found.
            HTTPException 410: If project is deleted.
            HTTPException 400: For invalid cursor format or other errors.
        """
        try:
            try:
                await project_service.get_project_info(project_id)
            except project_errors.ProjectNotFoundError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
                )
            except project_errors.ProjectDeletedError as e:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE, detail=str(e)
                )

            cursor_date = None
            if cursor:
                cursor_date = datetime.fromisoformat(cursor)

            publications_data = await project_service.get_publications(
                project_id, limit, cursor_date
            )

            publications = []
            for pub in publications_data:
                publication_dto = PublicationDTO(
                    id=pub["id"],
                    project_id=pub["project_id"],
                    label=pub["label"],
                    short_description=pub["short_description"],
                    created_at=pub["created_at"],
                    creator_id=pub["creator_id"],
                    creator_name=pub["creator_name"],
                    type=pub["type"],
                    answers_count=pub["answers_count"],
                    status=pub.get("status")
                )
                publications.append(publication_dto)

            next_cursor = None
            if publications and len(publications) == limit:
                next_cursor = publications[-1].created_at.isoformat()

            return {
                "items": publications,
                "next_cursor": next_cursor,
                "has_more": len(publications) == limit
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )

    @router.get("/profile/{profile_id}", response_model=MembershipsDTO)
    async def get_user_memberships(profile_id: UUID):
        """
        Get all project memberships for a user, grouped by role.

        Returns separate lists for scientist and volunteer roles.

        Args:
            profile_id: UUID of the user profile.

        Returns:
            MembershipsDTO with scientist and volunteer project lists.

        Raises:
            HTTPException 400: For errors during retrieval.
        """
        try:
            memberships = await project_service.get_user_memberships(profile_id)
            return MembershipsDTO(
                scientist=[
                    MembershipProjectDTO(
                        project_id=membership["project_id"],
                        label=membership["label"],
                        short_description=membership["short_description"],
                        created_at=membership["created_at"],
                        creator_name=membership["creator_name"],
                        status=membership["status"]
                    ) for membership in memberships[0]
                ],
                volunteer=[
                    MembershipProjectDTO(
                        project_id=membership["project_id"],
                        label=membership["label"],
                        short_description=membership["short_description"],
                        created_at=membership["created_at"],
                        creator_name=membership["creator_name"],
                        status=membership["status"]
                    ) for membership in memberships[1]
                ]
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            )

    return router
