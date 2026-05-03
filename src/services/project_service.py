from src.models.project import Project, Post, Task, DenormUser, TaskStatusEnum, ProjectStatusEnum, ProjectRoleEnum
from src.services.protocols import ProjectRepository, ProjectKafkaProducer
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors
from uuid import UUID, uuid4
from loguru import logger
from typing import Optional
from datetime import datetime


class ProjectService():
    def __init__(
        self,
        project_repository: ProjectRepository,
        kafka_producer: ProjectKafkaProducer
    ) -> None:
        self._project_repository = project_repository
        self._kafka_producer = kafka_producer

    async def _check_project_active(self, project_id: UUID) -> Project:
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

    async def _check_project_accessible(self, project_id: UUID) -> Project:
        try:
            project = await self._project_repository.get_project_info(project_id)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                f"Project {project_id} not found")

        if project["status"] == ProjectStatusEnum.DELETED:
            raise project_errors.ProjectDeletedError(
                f"Project {project_id} is deleted")

        return project

    async def create_project(self, project: Project) -> UUID:
        project.id = uuid4()

        try:
            await self._project_repository.create_project(project)
            await self._kafka_producer.send_create_project(project)
            return project.id
        except adapter_errors.ProjectAlreadyExistsError:
            raise project_errors.ProjectAlreadyExistsError(
                "Project with given name already exists.")

    async def update_project(self, project: Project) -> None:
        await self._check_project_active(project.id)

        try:
            await self._project_repository.update_project(project)
            await self._kafka_producer.send_update_project(project)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def get_project_info(self, id: UUID) -> dict:
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
        await self._check_project_accessible(id)

        try:
            statistics = await self._project_repository.get_project_statistics(id)
            return statistics
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def get_projects(self, ids: list[id]) -> list[Project]:
        try:
            projects = await self._project_repository.get_projects(ids)

            for project in projects:
                if project.status == ProjectStatusEnum.DELETED:
                    raise project_errors.ProjectDeletedError(
                        f"Project with ID {project.id} is deleted.")

            return projects
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def create_task(self, task: Task) -> UUID:
        await self._check_project_active(task.project_id)

        task.id = uuid4()
        try:
            await self._project_repository.create_task(task)
            await self._kafka_producer.send_create_task(task)
            return task.id
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def update_task(self, task: Task) -> None:
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

    async def get_task(self, id: UUID) -> Task:
        try:
            task = await self._project_repository.get_task(id)

            await self._check_project_accessible(task.project_id)

            return task
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this task doesn't exist")
        except adapter_errors.TaskNotFoundError:
            raise project_errors.TaskNotFoundError(
                "Couldn't find task by given ID")

    async def increment_task_answer(self, id: UUID) -> None:
        try:
            await self._project_repository.increment_task_answer(id)
        except adapter_errors.TaskNotFoundError:
            logger.warning(f"Task with id {id} doesn't exist")

    async def decrement_task_answer(self, id: UUID) -> None:
        try:
            await self._project_repository.decrement_task_answer(id)
        except adapter_errors.TaskNotFoundError:
            logger.warning(f"Task with id {id} doesn't exist")

    async def increment_post_answer(self, id: UUID) -> None:
        try:
            await self._project_repository.increment_post_answer(id)
        except adapter_errors.PostNotFoundError:
            logger.warning(f"Post with id {id} doesn't exist")

    async def decrement_post_answer(self, id: UUID) -> None:
        try:
            await self._project_repository.decrement_post_answer(id)
        except adapter_errors.PostNotFoundError:
            logger.warning(f"Post with id {id} doesn't exist")

    async def create_post(self, post: Post) -> UUID:
        await self._check_project_active(post.project_id)

        post.id = uuid4()
        try:
            await self._project_repository.create_post(post)
            await self._kafka_producer.send_create_post(post)
            return post.id
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this post doesn't exist")
        except adapter_errors.PostAlreadyExistsError:
            raise project_errors.PostAlreadyExistsError(
                "Post with given ID already exists")

    async def update_post(self, post: Post) -> None:
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
        try:
            post = await self._project_repository.get_post(id)
        except adapter_errors.PostNotFoundError:
            raise project_errors.PostNotFoundError(
                "Couldn't find post by given ID")

        await self._check_project_active(post.project_id)

        try:
            await self._project_repository.delete_post(id)
            await self._kafka_producer.send_delete_post(id)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this post doesn't exist")
        except adapter_errors.PostNotFoundError:
            raise project_errors.PostNotFoundError(
                "Couldn't find post by given ID")

    async def get_post(self, id: UUID) -> Post:
        try:
            post = await self._project_repository.get_post(id)
            await self._check_project_accessible(post.project_id)
            return post
        except adapter_errors.PostNotFoundError:
            raise project_errors.PostNotFoundError(
                "Couldn't find post by given ID")

    async def get_user_memberships(
        self, user_id: UUID
    ) -> list[list[dict]]:
        try:
            memberships = await self._project_repository.get_user_memberships(user_id)
            return memberships
        except adapter_errors.UserNotFoundError:
            raise project_errors.UserNotFoundError(
                "Couldn't find user by given ID")

    async def add_member(self, project_id: UUID, user: DenormUser) -> None:
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
        await self._check_project_accessible(project_id)

        try:
            publications = await self._project_repository.get_project_publications(project_id, limit, cursor)
            return publications
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def upsert_denorm_user(self, user: DenormUser) -> None:
        try:
            await self._project_repository.upsert_denorm_user(user)
        except adapter_errors.UserNotFoundError:
            raise project_errors.UserNotFoundError(
                "Couldn't find user by given ID")
