from src.models.project import Project, Post, Task, DenormUser, ProjectStatusEnum
from src.services.protocols import ProjectRepository, ProjectKafkaProducer
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors
from uuid import UUID, uuid4
from loguru import logger
from typing import Optional
from datetime import datetime


class ProjectService():
    """
    Service layer for project domain business logic.

    Provides methods for CRUD operations on projects, tasks, and posts,
    with automatic validation of project state (active, deleted, finished)
    and Kafka event publishing for state changes.
    """

    def __init__(
        self,
        project_repository: ProjectRepository,
        kafka_producer: ProjectKafkaProducer
    ) -> None:
        """
        Initialize the project service with dependencies.

        Args:
            project_repository: Repository for database operations.
            kafka_producer: Producer for publishing domain events.
        """
        self._project_repository = project_repository
        self._kafka_producer = kafka_producer

    async def _check_project_active(self, project_id: UUID) -> dict:
        """
        Check if a project exists and is in ACTIVE state.

        Validates that the project exists and is neither DELETED nor FINISHED.
        Used for operations that modify project content.

        Args:
            project_id: UUID of the project to check.

        Returns:
            Dictionary with project information.

        Raises:
            project_errors.ProjectNotFoundError: If project doesn't exist.
            project_errors.ProjectDeletedError: If project is deleted.
            project_errors.ProjectFinishedError: If project is finished.
        """
        try:
            project = await self._project_repository.get_project_info(project_id)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                f"Project {project_id} not found")

        if project["status"] == ProjectStatusEnum.DELETED:
            raise project_errors.ProjectDeletedError(
                f"Project {project_id} is deleted")
        if project["status"] == ProjectStatusEnum.FINISHED:
            raise project_errors.ProjectFinishedError(
                f"Project {project_id} is finished")

        return project

    async def _check_project_accessible(self, project_id: UUID) -> dict:
        """
        Check if a project exists and is accessible (not deleted).

        Validates that the project exists and is not DELETED.
        Used for read operations where finished projects are still accessible.

        Args:
            project_id: UUID of the project to check.

        Returns:
            Dictionary with project information.

        Raises:
            project_errors.ProjectNotFoundError: If project doesn't exist.
            project_errors.ProjectDeletedError: If project is deleted.
        """
        try:
            project = await self._project_repository.get_project_info(project_id)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                f"Project {project_id} not found")

        if project["status"] == ProjectStatusEnum.DELETED:
            raise project_errors.ProjectDeletedError(
                f"Project {project_id} is deleted")

        return project

    async def create_project(self, project: Project, creator_name: str = "") -> UUID:
        """
        Create a new project.

        Generates a unique ID for the project, persists it to the database,
        and publishes a project.created event.

        Args:
            project: Project object to create (ID can be None).
            creator_name: Display name of the creator for the Kafka event.

        Returns:
            UUID of the newly created project.

        Raises:
            project_errors.ProjectAlreadyExistsError: If project with same ID exists.
        """
        project.id = uuid4()

        try:
            await self._project_repository.create_project(project)
            await self._kafka_producer.send_create_project(project, creator_name=creator_name)
            return project.id
        except adapter_errors.ProjectAlreadyExistsError:
            raise project_errors.ProjectAlreadyExistsError(
                "Project with given name already exists.")

    async def update_project(self, project: Project) -> None:
        """
        Update an existing project.

        Validates project is active before updating, persists changes,
        and publishes a project.updated event.

        Args:
            project: Project object with updated data.

        Raises:
            project_errors.ProjectNotFoundError: If project doesn't exist.
            project_errors.ProjectDeletedError: If project is deleted.
            project_errors.ProjectFinishedError: If project is finished.
        """
        if project.id is None:
            raise project_errors.ProjectNotFoundError(
                "Project id is required for update")

        try:
            current_project = await self._project_repository.get_project_info(project.id)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                f"Project {project.id} not found")

        if current_project["status"] == ProjectStatusEnum.DELETED:
            raise project_errors.ProjectDeletedError(
                f"Project {project.id} is deleted")
        if current_project["status"] == ProjectStatusEnum.FINISHED and project.status != ProjectStatusEnum.ACTIVE:
            raise project_errors.ProjectFinishedError(
                f"Project {project.id} is finished")

        try:
            await self._project_repository.update_project(project)
            await self._kafka_producer.send_update_project(project)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def get_project_info(self, id: UUID) -> dict:
        """
        Retrieve detailed information about a project.

        Args:
            id: UUID of the project to retrieve.

        Returns:
            Dictionary containing project details.

        Raises:
            project_errors.ProjectNotFoundError: If project doesn't exist.
            project_errors.ProjectDeletedError: If project is deleted.
        """
        try:
            project = await self._project_repository.get_project_info(id)

            if project["status"] == ProjectStatusEnum.DELETED:
                raise project_errors.ProjectDeletedError(
                    "Project with given ID is deleted.")

            return project
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def get_project_statistics(self, id: UUID) -> dict:
        """
        Get aggregated statistics for a project.

        Args:
            id: UUID of the project.

        Returns:
            Dictionary with members_count, tasks_count, answers_count.

        Raises:
            project_errors.ProjectNotFoundError: If project doesn't exist.
            project_errors.ProjectDeletedError: If project is deleted.
        """
        await self._check_project_accessible(id)

        try:
            statistics = await self._project_repository.get_project_statistics(id)
            return statistics
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def get_projects(self, ids: list[UUID]) -> list[dict]:
        """
        Retrieve multiple projects by their IDs.

        Args:
            ids: List of project UUIDs to fetch.

        Returns:
            List of dictionaries with project details.

        Raises:
            project_errors.ProjectDeletedError: If any project is deleted.
            project_errors.ProjectNotFoundError: If any project doesn't exist.
        """
        try:
            projects = await self._project_repository.get_projects(ids)

            for project in projects:
                if project["status"] == ProjectStatusEnum.DELETED:
                    raise project_errors.ProjectDeletedError(
                        f"Project with ID {project["id"]} is deleted.")
            return projects

        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def create_task(self, task: Task, creator_name: str = "") -> UUID:
        """
        Create a new task within a project.

        Validates project is active, generates task ID, persists to database,
        and publishes a task.created event.

        Args:
            task: Task object to create (ID can be None).
            creator_name: Display name of the creator for the Kafka event.

        Returns:
            UUID of the newly created task.

        Raises:
            project_errors.ProjectNotFoundError: If project doesn't exist.
            project_errors.ProjectDeletedError: If project is deleted.
            project_errors.ProjectFinishedError: If project is finished.
        """
        await self._check_project_active(task.project_id)

        task.task_id = uuid4()
        try:
            await self._project_repository.create_task(task)
            await self._kafka_producer.send_create_task(task, creator_name=creator_name)
            return task.task_id
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def update_task(self, task: Task) -> None:
        """
        Update an existing task.

        Validates project is active, persists changes,
        and publishes a task.updated event.

        Args:
            task: Task object with updated data.

        Raises:
            project_errors.ProjectNotFoundError: If project doesn't exist.
            project_errors.ProjectDeletedError: If project is deleted.
            project_errors.ProjectFinishedError: If project is finished.
            project_errors.TaskNotFoundError: If task doesn't exist.
        """
        await self._check_project_active(task.project_id)

        try:
            await self._project_repository.update_task(task)
            await self._kafka_producer.send_update_task(task)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this task doesn't exist")
        except adapter_errors.TaskNotFoundError:
            raise project_errors.TaskNotFoundError(
                "Couldn't find task by given ID")

    async def get_task(self, id: UUID) -> dict:
        """
        Retrieve detailed information about a task.

        Args:
            id: UUID of the task to retrieve.

        Returns:
            Dictionary containing task details.

        Raises:
            project_errors.ProjectNotFoundError: If parent project doesn't exist.
            project_errors.ProjectDeletedError: If parent project is deleted.
            project_errors.TaskNotFoundError: If task doesn't exist.
        """
        try:
            task = await self._project_repository.get_task(id)

            await self._check_project_accessible(task["project_id"])

            return task

        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this task doesn't exist")
        except adapter_errors.TaskNotFoundError:
            raise project_errors.TaskNotFoundError(
                "Couldn't find task by given ID")

    async def increment_task_answer(self, id: UUID) -> None:
        """
        Increment the answer count for a task.

        Used when a new answer is submitted to a task.
        Logs a warning if task doesn't exist (idempotent operation).

        Args:
            id: UUID of the task to update.
        """
        try:
            await self._project_repository.increment_task_answer(id)
        except adapter_errors.TaskNotFoundError:
            logger.warning(f"Task with id {id} doesn't exist")

    async def decrement_task_answer(self, id: UUID) -> None:
        """
        Decrement the answer count for a task.

        Used when an answer is removed from a task.
        Logs a warning if task doesn't exist (idempotent operation).

        Args:
            id: UUID of the task to update.
        """
        try:
            await self._project_repository.decrement_task_answer(id)
        except adapter_errors.TaskNotFoundError:
            logger.warning(f"Task with id {id} doesn't exist")

    async def increment_post_answer(self, id: UUID) -> None:
        """
        Increment the comments/answers count for a post.

        Used when a new comment is added to a post.
        Logs a warning if post doesn't exist (idempotent operation).

        Args:
            id: UUID of the post to update.
        """
        try:
            await self._project_repository.increment_post_answer(id)
        except adapter_errors.PostNotFoundError:
            logger.warning(f"Post with id {id} doesn't exist")

    async def decrement_post_answer(self, id: UUID) -> None:
        """
        Decrement the comments/answers count for a post.

        Used when a comment is removed from a post.
        Logs a warning if post doesn't exist (idempotent operation).

        Args:
            id: UUID of the post to update.
        """
        try:
            await self._project_repository.decrement_post_answer(id)
        except adapter_errors.PostNotFoundError:
            logger.warning(f"Post with id {id} doesn't exist")

    async def create_post(self, post: Post, creator_name: str = "") -> UUID:
        """
        Create a new post within a project.

        Validates project is active, generates post ID, persists to database,
        and publishes a post.created event.

        Args:
            post: Post object to create (ID can be None).
            creator_name: Display name of the creator for the Kafka event.

        Returns:
            UUID of the newly created post.

        Raises:
            project_errors.ProjectNotFoundError: If project doesn't exist.
            project_errors.ProjectDeletedError: If project is deleted.
            project_errors.ProjectFinishedError: If project is finished.
            project_errors.PostAlreadyExistsError: If post with same ID exists.
        """
        await self._check_project_active(post.project_id)

        post.post_id = uuid4()
        try:
            await self._project_repository.create_post(post)
            await self._kafka_producer.send_create_post(post, creator_name=creator_name)
            return post.post_id
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this post doesn't exist")
        except adapter_errors.PostAlreadyExistsError:
            raise project_errors.PostAlreadyExistsError(
                "Post with given ID already exists")

    async def update_post(self, post: Post) -> None:
        """
        Update an existing post.

        Validates project is active, persists changes,
        and publishes a post.updated event.

        Args:
            post: Post object with updated data.

        Raises:
            project_errors.ProjectNotFoundError: If project doesn't exist.
            project_errors.ProjectDeletedError: If project is deleted.
            project_errors.ProjectFinishedError: If project is finished.
            project_errors.PostNotFoundError: If post doesn't exist.
        """
        await self._check_project_active(post.project_id)

        try:
            await self._project_repository.update_post(post)
            await self._kafka_producer.send_update_post(post)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this post doesn't exist")
        except adapter_errors.PostNotFoundError:
            raise project_errors.PostNotFoundError(
                "Couldn't find post by given ID")

    async def delete_post(self, id: UUID) -> None:
        """
        Delete a post.

        Validates post exists and its parent project is active,
        then deletes the post and publishes a post.deleted event.

        Args:
            id: UUID of the post to delete.

        Raises:
            project_errors.PostNotFoundError: If post doesn't exist.
            project_errors.ProjectNotFoundError: If parent project doesn't exist.
            project_errors.ProjectDeletedError: If parent project is deleted.
            project_errors.ProjectFinishedError: If parent project is finished.
        """
        try:
            post = await self._project_repository.get_post(id)
        except adapter_errors.PostNotFoundError:
            raise project_errors.PostNotFoundError(
                "Couldn't find post by given ID")

        await self._check_project_active(post["project_id"])

        try:
            await self._project_repository.delete_post(id)
            await self._kafka_producer.send_delete_post(id)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this post doesn't exist")
        except adapter_errors.PostNotFoundError:
            raise project_errors.PostNotFoundError(
                "Couldn't find post by given ID")

    async def get_post(self, id: UUID) -> dict:
        """
        Retrieve detailed information about a post.

        Args:
            id: UUID of the post to retrieve.

        Returns:
            Dictionary containing post details.

        Raises:
            project_errors.PostNotFoundError: If post doesn't exist.
            project_errors.ProjectNotFoundError: If parent project doesn't exist.
            project_errors.ProjectDeletedError: If parent project is deleted.
        """
        try:
            post = await self._project_repository.get_post(id)
            await self._check_project_accessible(post["project_id"])
            return post
        except adapter_errors.PostNotFoundError:
            raise project_errors.PostNotFoundError(
                "Couldn't find post by given ID")

    async def get_user_memberships(self, user_id: UUID) -> list[list[dict]]:
        """
        Get all project memberships for a user, grouped by role.

        Args:
            user_id: UUID of the user.

        Returns:
            List containing two lists: [scientist_projects, volunteer_projects].

        Raises:
            project_errors.UserNotFoundError: If user doesn't exist.
        """
        try:
            memberships = await self._project_repository.get_user_memberships(user_id)
            return memberships
        except adapter_errors.UserNotFoundError:
            raise project_errors.UserNotFoundError(
                "Couldn't find user by given ID")

    async def add_member(self, project_id: UUID, user: DenormUser) -> None:
        """
        Add a user as a member to a project.

        Validates project is active before adding the member.

        Args:
            project_id: UUID of the project.
            user: DenormUser object with user details and role.

        Raises:
            project_errors.ProjectNotFoundError: If project doesn't exist.
            project_errors.ProjectDeletedError: If project is deleted.
            project_errors.ProjectFinishedError: If project is finished.
            project_errors.UserAlreadyExistsError: If user is already a member.
        """
        await self._check_project_active(project_id)

        try:
            await self._project_repository.add_member(project_id, user)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")
        except adapter_errors.UserAlreadyExistsError:
            raise project_errors.UserAlreadyExistsError(
                "User is already a member of this project")

    async def remove_member(self, project_id: UUID, user_id: UUID) -> None:
        """
        Remove a user from a project membership.

        Validates project is active before removing the member.

        Args:
            project_id: UUID of the project.
            user_id: UUID of the user to remove.

        Raises:
            project_errors.ProjectNotFoundError: If project doesn't exist.
            project_errors.ProjectDeletedError: If project is deleted.
            project_errors.ProjectFinishedError: If project is finished.
            project_errors.UserNotFoundError: If user is not a member.
        """
        await self._check_project_active(project_id)

        try:
            await self._project_repository.remove_member(project_id, user_id)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")
        except adapter_errors.UserNotFoundError:
            raise project_errors.UserNotFoundError(
                "Couldn't find user by given ID")

    async def get_publications(
        self,
        project_id: UUID,
        limit: int = 20,
        cursor: Optional[datetime] = None
    ) -> list[dict]:
        """
        Get paginated list of publications (posts and tasks) for a project.

        Args:
            project_id: UUID of the project.
            limit: Maximum number of publications to return (default: 20).
            cursor: Optional datetime cursor for pagination.

        Returns:
            List of dictionaries containing publication details.

        Raises:
            project_errors.ProjectNotFoundError: If project doesn't exist.
            project_errors.ProjectDeletedError: If project is deleted.
        """
        await self._check_project_accessible(project_id)

        try:
            publications = await self._project_repository.get_project_publications(project_id, limit, cursor)
            return publications
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def upsert_denorm_user(self, user_id: UUID, data: dict) -> None:
        """
        Insert or update a denormalized user record.

        Used to sync user profile data from the user service.
        Logs operations for debugging and monitoring.

        Args:
            user_id: UUID of the user.
            data: Dictionary of user fields to upsert.

        Raises:
            project_errors.UserNotFoundError: If user doesn't exist in repository.
            Exception: For other errors during upsert operation.
        """
        try:
            logger.info(
                f"ProjectService.upsert_denorm_user called - user_id: {user_id}, data: {data}")
            await self._project_repository.upsert_denorm_user(user_id, data)
            logger.info(
                f"ProjectService.upsert_denorm_user completed successfully for user_id: {user_id}")
        except adapter_errors.UserNotFoundError:
            logger.error(f"User {user_id} not found in repository")
            raise project_errors.UserNotFoundError(
                "Couldn't find user by given ID")
        except Exception as e:
            logger.error(
                f"Error in upsert_denorm_user for user_id {user_id}: {e}", exc_info=True)
            raise
