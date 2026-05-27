from typing import Optional
import psycopg_pool
from uuid import UUID, uuid4
from datetime import datetime, timezone
from src.models.project import Project, Post, Task, DenormUser, Tag, ProjectStatusEnum, TaskStatusEnum
from psycopg import errors as psycopg_errors
import src.adapters.repository.errors as adapter_errors
from loguru import logger
from src.adapters.repository.postgres.queries import (
    TagQueries,
    ProjectQueries,
    TaskQueries,
    PostQueries,
    MembershipQueries,
)

_ALLOWED_DENORM_USER_COLUMNS = {"name", "email", "avatar_url"}


class ProjectPostgresRepository:
    """
    Repository for managing project-related data in PostgreSQL.

    Provides asynchronous methods for CRUD operations on projects, tasks, posts,
    tags, and project memberships. Uses connection pooling for database access.
    """

    def __init__(self, pool: psycopg_pool.AsyncConnectionPool) -> None:
        """
        Initialize the repository with a database connection pool.

        Args:
            pool: Async connection pool for PostgreSQL database access.
        """
        self._pool = pool

    async def _upsert_tag(self, conn, tag: Tag) -> UUID:
        """
        Insert or update a tag, returning its ID.

        If a tag with the same name exists, increments its count.
        Otherwise, creates a new tag entry.

        Args:
            conn: Active database connection.
            tag: Tag object to upsert.

        Returns:
            UUID of the tag (existing or newly created).
        """
        tag_id = tag.tag_id or uuid4()

        await conn.execute(
            TagQueries.UPSERT_TAG,
            (
                tag_id,
                tag.name,
                tag.quantity_count or 1
            )
        )

        result = await conn.execute(
            TagQueries.SELECT_TAG_ID_BY_NAME,
            (tag.name,)
        )
        row = await result.fetchone()
        if not row:
            raise adapter_errors.TagNotFoundError(
                f"Tag '{tag.name}' not found after upsert")
        return row[0]

    async def create_project(self, project: Project) -> UUID:
        """
        Create a new project in the database.

        Args:
            project: Project object containing the project data.

        Returns:
            UUID of the newly created project.

        Raises:
            ProjectAlreadyExistsError: If a project with the same ID already exists.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                project_id = project.id or uuid4()
                now = datetime.now(timezone.utc)

                try:
                    await conn.execute(
                        ProjectQueries.INSERT_PROJECT,
                        (
                            project_id,
                            project.label,
                            project.short_description,
                            project.description,
                            project.creator_id,
                            project.status.value,
                            project.created_at or now,
                            project.updated_at or now
                        )
                    )
                except psycopg_errors.UniqueViolation as e:
                    raise adapter_errors.ProjectAlreadyExistsError(
                        f"Project with id {project_id} already exists"
                    ) from e

                if project.tags:
                    for tag in project.tags:
                        tag_id = await self._upsert_tag(conn, tag)

                        await conn.execute(
                            ProjectQueries.INSERT_PROJECT_TAG_CONNECTION,
                            (project_id, tag_id)
                        )

                await conn.execute(
                    MembershipQueries.INSERT_MEMBERSHIP,
                    (project_id, project.creator_id, 'SCIENTIST')
                )

                return project_id

    async def get_project_info(self, id: UUID) -> dict:
        """
        Retrieve detailed information about a specific project.

        Args:
            id: UUID of the project to retrieve.

        Returns:
            Dictionary containing project details including tags and creator name.

        Raises:
            ProjectNotFoundError: If no project exists with the given ID.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    ProjectQueries.SELECT_PROJECT_INFO,
                    (id,)
                )

                row = await result.fetchone()

                if not row:
                    raise adapter_errors.ProjectNotFoundError(
                        f"Project with id {id} wasn't found"
                    )

                tags_result = await conn.execute(
                    ProjectQueries.SELECT_PROJECT_TAGS,
                    (id,)
                )
                tags_rows = await tags_result.fetchall()

                tags = [
                    Tag(tag_id=tag_row[0], name=tag_row[1],
                        quantity_count=tag_row[2])
                    for tag_row in tags_rows
                ]

                return {
                    "id": row[0],
                    "label": row[1],
                    "description": row[2],
                    "creator_id": row[3],
                    "creator_name": row[4],
                    "status": ProjectStatusEnum(row[5]),
                    "created_at": row[6],
                    "tags": tags
                }

    async def get_project_statistics(self, id: UUID) -> dict:
        """
        Get aggregated statistics for a project.

        Args:
            id: UUID of the project.

        Returns:
            Dictionary containing members_count, tasks_count, and answers_count.

        Raises:
            ProjectNotFoundError: If no project exists with the given ID.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    ProjectQueries.SELECT_PROJECT_STATISTICS,
                    (id,)
                )

                row = await result.fetchone()

                if not row:
                    raise adapter_errors.ProjectNotFoundError(
                        f"Project with id {id} not found"
                    )

                members_count = row[0] if row[0] is not None else 0
                tasks_count = row[1] if row[1] is not None else 0
                answers_count = row[2] if row[2] is not None else 0

                return {
                    "project_id": str(id),
                    "members_count": members_count,
                    "tasks_count": tasks_count,
                    "answers_count": answers_count
                }

    async def update_project(self, project: Project) -> None:
        """
        Update an existing project's information.

        Args:
            project: Project object with updated data.

        Raises:
            ProjectNotFoundError: If no project exists with the given ID.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                now = datetime.now(timezone.utc)

                result = await conn.execute(
                    ProjectQueries.UPDATE_PROJECT,
                    (
                        project.label,
                        project.short_description,
                        project.description,
                        now,
                        project.status.value,
                        project.id
                    )
                )

                row = await result.fetchone()
                if not row:
                    raise adapter_errors.ProjectNotFoundError(
                        f"Project with id {project.id} not found"
                    )

                if project.tags is not None:
                    await conn.execute(
                        ProjectQueries.DELETE_PROJECT_TAG_CONNECTIONS,
                        (project.id,)
                    )

                    for tag in project.tags:
                        tag_id = await self._upsert_tag(conn, tag)
                        await conn.execute(
                            ProjectQueries.INSERT_PROJECT_TAG_CONNECTION_NO_CONFLICT,
                            (project.id, tag_id)
                        )

    async def get_projects(self, ids: list[UUID]) -> list[dict]:
        """
        Retrieve multiple projects by their IDs.

        Args:
            ids: List of project UUIDs to retrieve.

        Returns:
            List of dictionaries containing project details with tags.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    ProjectQueries.SELECT_PROJECTS_BY_IDS,
                    (ids,)
                )

                rows = await result.fetchall()

                projects = []
                for row in rows:
                    tags_result = await conn.execute(
                        ProjectQueries.SELECT_PROJECT_TAGS,
                        (row[0],)
                    )
                    tags_rows = await tags_result.fetchall()

                    tags = [
                        Tag(tag_id=tag_row[0], name=tag_row[1],
                            quantity_count=tag_row[2])
                        for tag_row in tags_rows
                    ]

                    projects.append({
                        "id": row[0],
                        "label": row[1],
                        "short_description": row[2],
                        "description": row[3],
                        "creator_id": row[4],
                        "creator": row[5],
                        "status": ProjectStatusEnum(row[6]),
                        "created_at": row[7],
                        "updated_at": row[8],
                        "tags": tags
                    })

                return projects

    async def create_task(self, task: Task) -> UUID:
        """
        Create a new task in the database.

        Args:
            task: Task object containing the task data.

        Returns:
            UUID of the newly created task.

        Raises:
            TaskAlreadyExistsError: If a task with the same ID already exists.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                task_id = task.task_id or uuid4()
                now = datetime.now(timezone.utc)

                try:
                    await conn.execute(
                        TaskQueries.INSERT_TASK,
                        (
                            task_id,
                            task.project_id,
                            task.label,
                            task.creator_id,
                            task.short_description,
                            task.description,
                            task.created_at or now,
                            task.updated_at or now,
                            task.answers_count or 0,
                            task.status.value,
                            task.media_ids or []
                        )
                    )
                except psycopg_errors.UniqueViolation as e:
                    raise adapter_errors.TaskAlreadyExistsError(
                        f"Task with id {task_id} already exists"
                    ) from e

                return task_id

    async def update_task(self, task: Task) -> None:
        """
        Update an existing task's information.

        Args:
            task: Task object with updated data.

        Raises:
            TaskNotFoundError: If no task exists with the given ID.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                task_id = task.task_id
                now = datetime.now(timezone.utc)

                result = await conn.execute(
                    TaskQueries.UPDATE_TASK,
                    (
                        task.project_id,
                        task.label,
                        task.creator_id,
                        task.short_description,
                        task.description,
                        task.updated_at or now,
                        task.status.value,
                        task_id,
                    )
                )

                row = await result.fetchone()
                if not row:
                    raise adapter_errors.TaskNotFoundError(
                        f"Task with id {task_id} not found"
                    )

    async def get_task(self, id: UUID) -> dict:
        """
        Retrieve detailed information about a specific task.

        Args:
            id: UUID of the task to retrieve.

        Returns:
            Dictionary containing task details including creator name.

        Raises:
            TaskNotFoundError: If no task exists with the given ID.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    TaskQueries.SELECT_TASK,
                    (id,)
                )

                rows = await result.fetchall()
                if not rows:
                    raise adapter_errors.TaskNotFoundError(
                        f"Task with id {id} not found"
                    )

                return {
                    "task_id": rows[0][0],
                    "project_id": rows[0][1],
                    "label": rows[0][2],
                    "short_description": rows[0][3],
                    "description": rows[0][4],
                    "creator_id": rows[0][5],
                    "creator_name": rows[0][6],
                    "status": TaskStatusEnum(rows[0][7]),
                    "created_at": rows[0][8],
                    "updated_at": rows[0][9],
                    "answers_count": rows[0][10],
                    "media_ids": rows[0][11] or []
                }

    async def increment_post_answer(self, id: UUID) -> None:
        """
        Increment the comments/answers count for a post.

        Args:
            id: UUID of the post to update.

        Raises:
            PostNotFoundError: If no post exists with the given ID.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    PostQueries.INCREMENT_POST_ANSWER,
                    (id,)
                )

                updated_id = await result.fetchone()
                if not updated_id:
                    raise adapter_errors.PostNotFoundError(
                        f"Post with id {id} doesn't exist"
                    )

    async def decrement_post_answer(self, id: UUID) -> None:
        """
        Decrement the comments/answers count for a post.

        Args:
            id: UUID of the post to update.

        Raises:
            PostNotFoundError: If no post exists with the given ID.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    PostQueries.DECREMENT_POST_ANSWER,
                    (id,)
                )

                updated_id = await result.fetchone()
                if not updated_id:
                    raise adapter_errors.PostNotFoundError(
                        f"Post with id {id} doesn't exist"
                    )

    async def increment_task_answer(self, id: UUID) -> None:
        """
        Increment the answer count for a task.

        Args:
            id: UUID of the task to update.

        Raises:
            PostNotFoundError: If no task exists with the given ID.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    TaskQueries.INCREMENT_TASK_ANSWER,
                    (id,)
                )

                updated_id = await result.fetchone()
                if not updated_id:
                    raise adapter_errors.TaskNotFoundError(
                        f"Task with id {id} doesn't exist"
                    )

    async def decrement_task_answer(self, id: UUID) -> None:
        """
        Decrement the answer count for a task.

        Args:
            id: UUID of the task to update.

        Raises:
            PostNotFoundError: If no task exists with the given ID.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    TaskQueries.DECREMENT_TASK_ANSWER,
                    (id,)
                )

                updated_id = await result.fetchone()
                if not updated_id:
                    raise adapter_errors.TaskNotFoundError(
                        f"Task with id {id} doesn't exist"
                    )

    async def create_post(self, post: Post) -> UUID:
        """
        Create a new post in the database.

        Args:
            post: Post object containing the post data.

        Returns:
            UUID of the newly created post.

        Raises:
            PostAlreadyExistsError: If a post with the same ID already exists.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                post_id = post.post_id or uuid4()
                now = datetime.now(timezone.utc)

                try:
                    await conn.execute(
                        PostQueries.INSERT_POST,
                        (
                            post_id,
                            post.project_id,
                            post.label,
                            post.creator_id,
                            post.short_description,
                            post.description,
                            post.comments_count or 0,
                            post.created_at or now,
                            post.updated_at or now,
                            post.media_ids or []
                        )
                    )
                except psycopg_errors.UniqueViolation as e:
                    raise adapter_errors.PostAlreadyExistsError(
                        f"Post with id {post_id} already exists"
                    ) from e

                return post_id

    async def update_post(self, post: Post) -> None:
        """
        Update an existing post's information.

        Args:
            post: Post object with updated data.

        Raises:
            TaskNotFoundError: If no post exists with the given ID.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                post_id = post.post_id
                now = datetime.now(timezone.utc)

                result = await conn.execute(
                    PostQueries.UPDATE_POST,
                    (
                        post.project_id,
                        post.label,
                        post.creator_id,
                        post.short_description,
                        post.description,
                        post.updated_at or now,
                        post_id,
                    )
                )

                row = await result.fetchone()
                if not row:
                    raise adapter_errors.PostNotFoundError(
                        f"Post with id {post_id} not found"
                    )

    async def delete_post(self, id: UUID) -> None:
        """
        Delete a post from the database.

        Args:
            id: UUID of the post to delete.

        Raises:
            PostNotFoundError: If no post exists with the given ID.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    PostQueries.DELETE_POST,
                    (id,)
                )

                delete_id = await result.fetchone()
                if not delete_id:
                    raise adapter_errors.PostNotFoundError(
                        f"Post with id {id} doesn't exist"
                    )

    async def get_post(self, id: UUID) -> dict:
        """
        Retrieve detailed information about a specific post.

        Args:
            id: UUID of the post to retrieve.

        Returns:
            Dictionary containing post details including creator name.

        Raises:
            PostNotFoundError: If no post exists with the given ID.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    PostQueries.SELECT_POST,
                    (id,)
                )

                rows = await result.fetchall()
                if not rows:
                    raise adapter_errors.PostNotFoundError(
                        f"Post with id {id} not found"
                    )

                return {
                    "post_id": rows[0][0],
                    "project_id": rows[0][1],
                    "label": rows[0][2],
                    "creator_id": rows[0][3],
                    "creator_name": rows[0][4],
                    "short_description": rows[0][5],
                    "description": rows[0][6],
                    "comments_count": rows[0][7],
                    "created_at": rows[0][8],
                    "updated_at": rows[0][9],
                    "media_ids": rows[0][10] or []
                }

    async def get_user_memberships(self, user_id: UUID) -> list[list[dict]]:
        """
        Get all project memberships for a user, separated by role.

        Args:
            user_id: UUID of the user.

        Returns:
            List containing two lists: [scientist_projects, volunteer_projects].
            Each project contains basic project information and the user's role.
        """
        async with self._pool.connection() as conn:
            result = await conn.execute(
                MembershipQueries.SELECT_USER_MEMBERSHIPS,
                (user_id,)
            )

            rows = await result.fetchall()

            scientist_projects = []
            volunteer_projects = []

            for row in rows:
                role = row[5]

                project = {
                    "project_id": row[0],
                    "label": row[1],
                    "short_description": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "creator_name": row[6] or "Unknown",
                }

                if role == 'SCIENTIST':
                    scientist_projects.append(project)
                elif role == 'VOLUNTEER':
                    volunteer_projects.append(project)

            return [scientist_projects, volunteer_projects]

    async def add_member(self, project_id: UUID, user: DenormUser) -> None:
        """
        Add a user as a member to a project with specified role.

        Args:
            project_id: UUID of the project.
            user: DenormUser object containing user ID and role.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    MembershipQueries.UPSERT_MEMBER,
                    (project_id, user.id, user.role)
                )

    async def remove_member(self, project_id: UUID, user_id: UUID) -> None:
        """
        Remove a user from a project membership.

        Args:
            project_id: UUID of the project.
            user_id: UUID of the user to remove.

        Raises:
            UserNotFoundError: If the user is not a member of the project.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    MembershipQueries.DELETE_MEMBER,
                    (project_id, user_id)
                )

                row = await result.fetchone()
                if not row:
                    raise adapter_errors.UserNotFoundError(
                        f"User {user_id} not found in project {project_id}"
                    )

    async def get_project_publications(
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
            cursor: Optional datetime cursor for pagination (returns older items).

        Returns:
            List of dictionaries containing publication details including type
            (post or task), status, and answers count, ordered by creation date.
        """
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    ProjectQueries.SELECT_PROJECT_PUBLICATIONS,
                    (
                        project_id, cursor, cursor,
                        project_id, cursor, cursor,
                        limit
                    )
                )

                rows = await result.fetchall()

                publications = []
                for row in rows:
                    publications.append({
                        "id": row[0],
                        "project_id": row[1],
                        "label": row[2],
                        "short_description": row[3],
                        "created_at": row[4],
                        "creator_id": row[5],
                        "creator_name": row[6],
                        "type": row[7],
                        "status": row[8],
                        "answers_count": row[9],
                        "media_ids": row[10] or []
                    })

                return publications

    async def upsert_denorm_user(self, user_id: UUID, data: dict) -> None:
        """
        Insert or update a denormalized user record.

        Dynamically builds an INSERT ... ON CONFLICT UPDATE query based on
        the provided data fields. Ensures avatar_url is always present.

        Args:
            user_id: UUID of the user.
            data: Dictionary of user fields to upsert (e.g., name, email, avatar_url).

        Raises:
            Exception: If database operation fails, logs error and re-raises.
        """
        logger.info(
            f"Repository.upsert_denorm_user called - user_id: {user_id}, data: {data}")

        unknown = set(data.keys()) - _ALLOWED_DENORM_USER_COLUMNS
        if unknown:
            raise ValueError(f"Unknown columns for denorm_user: {unknown}")

        if not data:
            data = {}
            logger.debug("No data provided, using empty dict")

        insert_data = dict(data)
        avatar_in_data = "avatar_url" in insert_data
        if not avatar_in_data:
            insert_data["avatar_url"] = ""

        insert_cols = ["id"] + list(insert_data.keys())
        placeholders = ", ".join(["%s"] * len(insert_cols))

        update_cols = [col for col in data.keys()]
        set_clauses = [f"{col} = EXCLUDED.{col}" for col in update_cols]
        on_conflict = ""
        if set_clauses:
            on_conflict = f"ON CONFLICT (id) DO UPDATE SET {', '.join(set_clauses)}"

        values = [user_id] + [insert_data[col] for col in insert_data.keys()]

        sql = f"""
            INSERT INTO denorm_user ({', '.join(insert_cols)})
            VALUES ({placeholders})
            {on_conflict}
        """

        logger.debug(f"Generated SQL: {sql}")
        logger.debug(f"SQL values: {values}")

        try:
            async with self._pool.connection() as conn:
                async with conn.transaction():
                    await conn.execute(sql, tuple(values))
            logger.info(
                f"Successfully inserted/updated denorm_user for user_id: {user_id}")
        except Exception as e:
            logger.error(
                f"Error executing upsert_denorm_user SQL for user_id {user_id}: {e}", exc_info=True)
            raise
