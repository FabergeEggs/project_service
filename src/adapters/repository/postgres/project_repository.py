import psycopg_pool
from uuid import UUID, uuid4
from datetime import datetime, timezone
from src.models.project import Project, Post, Task, DenormUser, Tag, ProjectStatusEnum, TaskStatusEnum
from psycopg import errors as psycopg_errors
import src.adapters.repository.errors as adapter_errors


class ProjectPostgresRepository:
    def __init__(self, pool: psycopg_pool.AsyncConnectionPool) -> None:
        self._pool = pool

    async def _upsert_tag(self, conn, tag: Tag) -> UUID:
        tag_id = tag.tag_id or uuid4()

        await conn.execute(
            """
            INSERT INTO tags (id, name, count)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                count = tags.count + 1
            """,
            (
                tag_id,
                tag.name,
                tag.quantity_count or 1
            )
        )

        result = await conn.execute(
            "SELECT id FROM tags WHERE name = %s",
            (tag.name,)
        )
        row = await result.fetchone()
        return row[0]

    async def create_project(self, project: Project) -> UUID:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                project_id = project.id or uuid4()
                now = datetime.now(timezone.utc)

                try:
                    await conn.execute(
                        """
                        INSERT INTO project (
                            id, label, short_description, description,
                            creator, status, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            project_id,
                            project.label,
                            project.short_description,
                            project.description,
                            project.creator,
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
                            """
                            INSERT INTO project_tag_connection (project_id, tag_id)
                            VALUES (%s, %s)
                            ON CONFLICT (project_id, tag_id) DO NOTHING
                            """,
                            (
                                project_id, tag_id
                            )
                        )

                return project_id

    async def get_project_info(self, id: UUID) -> Project:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    """
                    SELECT id, label, short_description, description,
                    creator, status, created_at, updated_at
                    FROM project
                    WHERE id = %s AND status != 'DELETED'
                    """,
                    (id,)
                )

                row = await result.fetchone()

                if not row:
                    raise adapter_errors.ProjectNotFoundError(
                        f"Project with id {id} was't found"
                    )

                tags_result = await conn.execute(
                    """
                    SELECT t.id, t.name, t.count
                    FROM tags t
                    JOIN project_tag_connection ptc ON ptc.tag_id = t.id
                    WHERE ptc.project_id = %s
                    """,
                    (id,)
                )
                tags_rows = await tags_result.fetchall()

                tags = [
                    Tag(tag_id=row[0], name=row[1], quantity_count=row[2])
                    for row in tags_rows
                ]

                return Project(
                    id=row[0],
                    label=row[1],
                    short_description=row[2],
                    description=row[3],
                    creator=row[4],
                    status=ProjectStatusEnum(row[5]),
                    created_at=row[6],
                    updated_at=row[7],
                    tags=tags
                )

    async def get_project_statistics(self, id: UUID) -> dict:
        async with self._pool.connection() as conn:
            result = await conn.execute(
                """
                SELECT
                    COUNT(DISTINCT puc.user_id) as members_count,
                    COUNT(t.id) as tasks_count,
                    COALESCE(SUM(t.answers_count), 0) as total_answers_count
                FROM project p
                LEFT JOIN project_user_connection puc
                    ON puc.project_id = p.id
                LEFT JOIN task t
                    ON t.project_id = p.id
                    AND t.status != 'DELETED'
                WHERE p.id = %s
                    AND p.status != 'DELETED'
                GROUP BY p.id
                """,
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
        async with self._pool.connection() as conn:
            async with conn.transaction():
                now = datetime.now(timezone.utc)

                result = await conn.execute(
                    """
                    UPDATE project
                    SET label = %s,
                        short_description = %s,
                        description = %s,
                        updated_at = %s,
                        status = %s
                    WHERE id = %s
                    RETURNING id
                    """,
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
                        "DELETE FROM project_tag_connection WHERE project_id = %s",
                        (project.id,)
                    )

                    for tag in project.tags:
                        tag_id = await self._upsert_tag(conn, tag)
                        await conn.execute(
                            """
                            INSERT INTO project_tag_connection (project_id, tag_id)
                            VALUES (%s, %s)
                            """,
                            (
                                project.id,
                                tag_id
                            )
                        )

    async def get_projects(self, ids: list[UUID]) -> list[Project]:
        async with self._pool.connection() as conn:
            result = await conn.execute(
                """
                SELECT id, label, short_description, description,
                creator, status, created_at, updated_at
                FROM project
                WHERE id = ANY(%s) AND status != 'DELETED'
                """,
                (ids,)
            )

            rows = await result.fetchall()

            projects = []
            for row in rows:
                tags_result = await conn.execute(
                    """
                    SELECT t.id, t.name, t.count
                    FROM tags t
                    JOIN project_tag_connection ptc ON ptc.tag_id = t.id
                    WHERE ptc.project_id = %s
                    """,
                    (row[0],)
                )
                tags_rows = await tags_result.fetchall()

                tags = [
                    Tag(tag_id=tag_row[0], name=tag_row[1],
                        quantity_count=tag_row[2])
                    for tag_row in tags_rows
                ]

                projects.append(Project(
                    id=row[0],
                    label=row[1],
                    short_description=row[2],
                    description=row[3],
                    creator=row[4],
                    status=ProjectStatusEnum(row[5]),
                    created_at=row[6],
                    updated_at=row[7],
                    tags=tags
                ))

            return projects

    async def create_task(self, task: Task) -> UUID:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                task_id = task.task_id or uuid4()
                now = datetime.now(timezone.utc)

                try:
                    await conn.execute(
                        """
                        INSERT INTO task (
                            id, project_id, label, creator,
                            short_description, description,
                            created_at, updated_at,
                            answer_count, status
                        ) VALUES (%s %s %s %s %s %s %s %s)
                        """,
                        (
                            task_id,
                            task.project_id,
                            task.label,
                            task.creator,
                            task.short_description,
                            task.description,
                            task.created_at or now,
                            task.updated_at or now,
                            task.answers_count or 0,
                            task.status.value
                        )
                    )
                except psycopg_errors.UniqueViolation as e:
                    raise adapter_errors.TaskAlreadyExistsError(
                        f"Task with id {task_id} already exists"
                    ) from e

                return task_id

    async def update_task(self, task: Task) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                task_id = task.task_id
                now = datetime.now(timezone.utc)

                result = await conn.execute(
                    """
                        UPDATE task
                        SET project_id = %s, label = %s, creator = %s,
                            short_description = %s, description = %s,
                            updated_at = %s, status = %s
                        WHERE id = %s
                        RETURNING id
                        """,
                    (
                        task.project_id,
                        task.label,
                        task.creator,
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

    async def get_task(self, id: UUID) -> Task:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = conn.execute(
                    """
                    SELECT t.id, t.project_id, t.label, t.creator,
                    t.short_description, t.description, t.created_at,
                    t.updated_at, t.status, t.answer_count
                    FROM task t
                    WHERE t.id = %s AND t.status != 'DELETED'
                    """,
                    (id,)
                )

                rows = await result.fetchall()

                if not rows:
                    raise adapter_errors.TaskNotFoundError(
                        f"Task with id {id} not found"
                    )

                return Task(
                    task_id=rows[0][0],
                    project_id=rows[0][1],
                    label=rows[0][2],
                    creator=rows[0][3],
                    short_description=rows[0][4],
                    description=rows[0][5],
                    created_at=rows[0][6],
                    updated_at=rows[0][7],
                    status=TaskStatusEnum(rows[0][8]),
                    answers_count=rows[0][9]
                )

    async def increment_task_answer(self, id: UUID) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    """
                        UPDATE task
                        SET answer_count = answer_count + 1,
                            updated_at = NOW()
                        WHERE id = %s AND status != 'DELETED'
                        RETURNING id
                        """,
                    (id,)
                )

                updated_id = await result.fetchone()
                if not updated_id:
                    raise adapter_errors.PostNotFoundError(
                        f"Post with id {id} doesn't exist"
                    )

    async def decrement_task_answer(self, id: UUID) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    """
                        UPDATE task
                        SET answer_count = answer_count - 1,
                            updated_at = NOW()
                        WHERE id = %s AND status != 'DELETED' AND answer_count > 0
                        RETURNING id
                        """,
                    (id,)
                )

                updated_id = await result.fetchone()
                if not updated_id:
                    raise adapter_errors.PostNotFoundError(
                        f"Post with id {id} doesn't exist"
                    )

    async def create_post(self, post: Post) -> UUID:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                post_id = post.post_id or uuid4()
                now = datetime.now(timezone.utc)

                try:
                    await conn.execute(
                        """
                        INSERTN INTO post (
                            id, project_id, label, creator,
                            short_description, description,
                            created_at, updated_at
                        ) VALUE
                        """,
                        (
                            post_id,
                            post.project_id,
                            post.label,
                            post.creator,
                            post.short_description,
                            post.description,
                            post.created_at or now,
                            post.updated_at or now
                        )
                    )
                except psycopg_errors.UniqueViolation as e:
                    raise adapter_errors.PostAlreadyExistsError(
                        f"Post with id {post_id} already exists"
                    ) from e

                return post_id

    async def update_post(self, post: Post) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                post_id = post.post_id
                now = datetime.now(timezone.utc)

                result = await conn.execute(
                    """
                        UPDATE post
                        SET project_id = %s, label = %s, creator = %s,
                            short_description = %s, description = %s,
                            updated_at = %s
                        WHERE id = %s
                        RETURNING id
                        """,
                    (
                        post.project_id,
                        post.label,
                        post.creator,
                        post.short_description,
                        post.description,
                        post.updated_at or now,
                        post_id,
                    )
                )

                row = await result.fetchone()
                if not row:
                    raise adapter_errors.TaskNotFoundError(
                        f"Task with id {post_id} not found"
                    )

    async def delete_post(self, id: UUID) -> None:
        async with self._pool.connection() as conn:
            async with conn.transaction():

                result = await conn.execute(
                    """
                        DELETE FROM post
                        WHERE id = %s
                        RETURNING id
                        """,
                    (id,)
                )

                delete_id = result.fetchone()
                if not delete_id:
                    raise adapter_errors.PostNotFoundError(
                        f"Post with id {id} doesn't exist"
                    )

    async def get_post(self, id: UUID) -> Post:
        async with self._pool.connection() as conn:
            async with conn.transaction():
                result = conn.execute(
                    """
                    SELECT t.id, t.project_id, t.label, t.creator,
                    t.short_description, t.description,
                    t.created_at, t.updated_at
                    FROM post t
                    WHERE t.id = %s
                    """,
                    (id,)
                )

                rows = await result.fetchall()

                if not rows:
                    raise adapter_errors.TaskNotFoundError(
                        f"Task with id {id} not found"
                    )

                return Task(
                    task_id=rows[0][0],
                    project_id=rows[0][1],
                    label=rows[0][2],
                    creator=rows[0][3],
                    short_description=rows[0][4],
                    description=rows[0][5],
                    created_at=rows[0][6],
                    updated_at=rows[0][7]
                )

    async def get_user_memberships(
            self, user_id: UUID) -> list[list[UUID]]:
        async with self._pool.connection() as conn:
            result = await conn.execute(
                """
                SELECT
                    p.id,
                    puc.role
                FROM project_user_connection puc
                JOIN project p ON p.id = puc.project_id
                WHERE puc.user_id = %s
                    AND p.status != 'DELETED'
                    AND puc.role != 'DELETED'
                """,
                (user_id,)
            )

            rows = await result.fetchall()

            scientist_projects = []
            volunteer_projects = []

            for row in rows:
                project_id = row[0]
                role = row[1]

                if role == 'scientist':
                    scientist_projects.append(project_id)
                elif role == 'volunteer':
                    volunteer_projects.append(project_id)

            return [scientist_projects, volunteer_projects]

    async def add_member(self, project_id: UUID, user: DenormUser) -> None: ...
    async def remove_member(self, id: UUID) -> None: ...
