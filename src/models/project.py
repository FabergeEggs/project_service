from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


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
    tag_id: uuid.UUID
    name: str


@dataclass
class Project:
    id: uuid.UUID
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
    post_id: uuid.UUID
    project_id: uuid.UUID
    label: str
    creator: str
    short_description: str
    description: str
    created_at: datetime


@dataclass
class Task:
    task_id: uuid.UUID
    project_id: uuid.UUID
    label: str
    creator: str
    short_description: str
    description: str
    created_at: datetime
    status: TaskStatusEnum
    answers_count: int = 0


@dataclass
class DenormUser:
    id: uuid.UUID
    name: str
    role: ProjectRoleEnum
    avatar_link: str
