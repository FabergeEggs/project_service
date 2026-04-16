from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


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
    tag_id: UUID
    name: str
    quantity_count: int = 0


@dataclass
class Project:
    id: UUID
    label: str
    creator: str
    short_description: str
    description: str
    tags: list[Tag]
    created_at: datetime
    updated_at: datetime
    status: ProjectStatusEnum


@dataclass
class Post:
    post_id: UUID
    project_id: UUID
    label: str
    creator: str
    short_description: str
    description: str
    created_at: datetime


@dataclass
class Task:
    task_id: UUID
    project_id: UUID
    label: str
    creator: str
    short_description: str
    description: str
    created_at: datetime
    status: TaskStatusEnum
    answers_count: int = 0


@dataclass
class DenormUser:
    id: UUID
    name: str
    role: ProjectRoleEnum
    avatar_link: str
