from datetime import datetime
from uuid import uuid4

from src.models.project import Project, Post, ProjectStatusEnum, Tag, Task, TaskStatusEnum


def _normalize_status(status: ProjectStatusEnum | str) -> ProjectStatusEnum:
    if isinstance(status, str):
        return ProjectStatusEnum(status)
    return status


def make_project_info(**kwargs) -> dict:
    """Dict shape returned by PostgresProjectRepository.get_project_info."""
    project_id = kwargs.pop("id", uuid4())
    status = _normalize_status(kwargs.pop("status", ProjectStatusEnum.ACTIVE))
    return {
        "id": project_id,
        "label": kwargs.get("label", "Test Project"),
        "description": kwargs.get("description", "Full description"),
        "creator_id": kwargs.get("creator_id", uuid4()),
        "creator_name": kwargs.get("creator_name", "Creator"),
        "status": status,
        "created_at": kwargs.get("created_at", datetime.now()),
        "tags": kwargs.get("tags", []),
    }


def make_project(**kwargs) -> Project:
    default = dict(
        id=uuid4(),
        label="Test Project",
        creator_id=uuid4(),
        short_description="Short test description",
        description="Full detailed description for testing purposes",
        tags=[Tag(tag_id=uuid4(), name="test_tag")],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status=ProjectStatusEnum.ACTIVE,
    )
    default.update(kwargs)
    if isinstance(default.get("status"), str):
        default["status"] = ProjectStatusEnum(default["status"])
    return Project(**default)


def make_task(**kwargs) -> Task:
    default = dict(
        task_id=uuid4(),
        project_id=uuid4(),
        creator_id=uuid4(),
        label="Test Task",
        short_description="Short task description",
        description="Full detailed task description for testing",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        status=TaskStatusEnum.ACTIVE,
        answers_count=0,
    )
    default.update(kwargs)
    if isinstance(default.get("status"), str):
        default["status"] = TaskStatusEnum(default["status"])
    return Task(**default)


def make_task_info(**kwargs) -> dict:
    task = make_task(**kwargs)
    return {
        "task_id": task.task_id,
        "project_id": task.project_id,
        "label": task.label,
        "short_description": task.short_description,
        "description": task.description,
        "creator_id": task.creator_id,
        "creator_name": kwargs.get("creator_name", "Creator"),
        "status": task.status,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "answers_count": task.answers_count,
    }


def make_post(**kwargs) -> Post:
    default = dict(
        post_id=uuid4(),
        project_id=uuid4(),
        creator_id=uuid4(),
        label="Test Post",
        short_description="Short post description",
        description="Full post description",
        comments_count=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    default.update(kwargs)
    return Post(**default)


def make_post_info(**kwargs) -> dict:
    post = make_post(**kwargs)
    return {
        "post_id": post.post_id,
        "project_id": post.project_id,
        "label": post.label,
        "creator_id": post.creator_id,
        "creator_name": kwargs.get("creator_name", "Creator"),
        "short_description": post.short_description,
        "description": post.description,
        "comments_count": post.comments_count,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }
