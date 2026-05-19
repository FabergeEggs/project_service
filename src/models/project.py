from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import Optional


class ProjectStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"
    DELETED = "DELETED"


class TaskStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"
    DELETED = "DELETED"


class ProjectRoleEnum(str, Enum):
    SCIENTIST = "SCIENTIST"
    VOLUNTEER = "VOLUNTEER"
    DELETED = "DELETED"


@dataclass
class Tag:
    tag_id: Optional[UUID]
    name: str
    quantity_count: int = 0


@dataclass
class Project:
    id: UUID
    label: str
    creator_id: UUID
    short_description: str
    description: str
    tags: list[Tag]
    created_at: datetime
    updated_at: datetime
    status: ProjectStatusEnum


@dataclass
class Post:
    post_id: Optional[UUID]
    project_id: UUID
    creator_id: UUID
    label: str
    short_description: str
    description: str
    comments_count: int
    created_at: datetime
    updated_at: datetime


@dataclass
class Task:
    task_id: Optional[UUID]
    project_id: UUID
    creator_id: UUID
    label: str
    short_description: str
    description: str
    created_at: datetime
    updated_at: datetime
    status: TaskStatusEnum
    answers_count: int = 0


@dataclass
class DenormUser:
    id: UUID
    name: str
    role: ProjectRoleEnum
    avatar_link: str
