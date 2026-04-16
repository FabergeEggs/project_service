from src.models.project import Project, Post, Task, DenormUser, TaskStatusEnum, ProjectStatusEnum, ProjectRoleEnum
from src.services.protocols import ProjectRepository, ProjectKafkaProducer
import src.services.errors as project_errors
import src.adapters.repository.errors as adapter_errors
from uuid import UUID, uuid4


class ProjectService():
    def __init__(
        self,
        project_repository: ProjectRepository,
        kafka_producer: ProjectKafkaProducer
    ) -> None:
        self._project_repository = project_repository
        self._kafka_producer = kafka_producer

    async def create_project(self, project: Project) -> UUID:
        project.id = uuid4()

        try:
            await self._project_repository.create_project(project)
            self._kafka_producer.send_create_project(project)
            return project.id
        except adapter_errors.ProjectAlreadyExistsError:
            raise project_errors.ProjectAlreadyExistsError(
                "Project with given name already exists.")

    async def update_project(self, project: Project) -> None:
        try:
            await self._project_repository.update_project(project)
            self._kafka_producer.send_update_project(project)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def get_project_info(self, id: UUID) -> Project:
        try:
            project = await self._project_repository.get_project_info(id)
            return project
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def get_project_statistics(self, id: UUID) -> dict:
        try:
            statistics = await self._project_repository.get_project_statistics(id)
            return statistics
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def get_projects(self, ids: list[id]) -> list[Project]:
        try:
            projects = await self._project_repository.get_projects(ids)
            return projects
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def create_task(self, task: Task) -> UUID:
        task.id = uuid4()
        try:
            await self._project_repository.create_task(task)
            return task.id
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")

    async def update_task(self, task: Task) -> None:
        try:
            await self._project_repository.update_task(task)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this task doesn't exist")
        except adapter_errors.TaskNotFoundError:
            raise project_errors.TaskNotFoundError(
                "Couldn't find task by given ID")

    async def get_project_tasks(self, id: UUID) -> list[Task]:
        try:
            tasks = await self._project_repository.get_project_tasks(id)
            return tasks
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this task doesn't exist")
        except adapter_errors.TaskNotFoundError:
            raise project_errors.TaskNotFoundError(
                "Couldn't find task by given ID")

    async def create_post(self, post: Post) -> UUID:
        post.id = uuid4()
        try:
            await self._project_repository.create_post(post)
            self._kafka_producer.send_create_post(post)
            return post.id
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this post doesn't exist")
        except adapter_errors.PostAlreadyExistsError:
            raise project_errors.PostAlreadyExistsError(
                "Post with given ID already exists")

    async def update_post(self, post: Post) -> None:
        try:
            await self._project_repository.update_post(post)
            self._kafka_producer.send_update_post(post)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this post doesn't exist")
        except adapter_errors.PostNotFoundError:
            raise project_errors.PostNotFoundError(
                "Couldn't find post by given ID")

    async def delete_post(self, id: UUID) -> None:
        try:
            await self._project_repository.delete_post(id)
            self._kafka_producer.send_delete_post(id)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this post doesn't exist")
        except adapter_errors.PostNotFoundError:
            raise project_errors.PostNotFoundError(
                "Couldn't find post by given ID")

    async def get_project_posts(self, id: UUID) -> list[Post]:
        try:
            posts = await self._project_repository.get_project_posts(id)
            return posts
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Project of this post doesn't exist")
        except adapter_errors.PostNotFoundError:
            raise project_errors.PostNotFoundError(
                "Couldn't find post by given ID")

    async def get_user_memberships(
            self, user_id: UUID) -> list[list[UUID]]:
        try:
            memberships = await self._project_repository.get_user_memberships(user_id)
            return memberships
        except adapter_errors.UserNotFoundError:
            raise project_errors.UserNotFoundError(
                "Couldn't find user by given ID")

    async def add_member(self, project_id: UUID, user: DenormUser) -> None:
        try:
            await self._project_repository.add_member(project_id, user)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")
        except adapter_errors.UserAlreadyExistsError:
            raise project_errors.UserAlreadyExistsError(
                "User is already a member of this project")

    async def remove_member(self, project_id: UUID, user_id: UUID) -> None:
        try:
            await self._project_repository.remove_member(project_id, user_id)
        except adapter_errors.ProjectNotFoundError:
            raise project_errors.ProjectNotFoundError(
                "Couldn't find project by given ID")
        except adapter_errors.UserNotFoundError:
            raise project_errors.UserNotFoundError(
                "Couldn't find user by given ID")
        except adapter_errors.UserAlreadyExistsError:
            raise project_errors.UserAlreadyExistsError(
                "User is not a member of this project")
