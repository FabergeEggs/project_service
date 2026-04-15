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
class Project:
    id: uuid.UUID
    label: str
    creator: str
    short_description: str
    description: str
    tags: list
    status: ProjectStatusEnum


@dataclass
class Post:
    id: uuid.UUID
    label: str
    creator: str
    short_description: str
    description: str
    project_id: uuid.UUID


@dataclass
class Task:
    id: uuid.UUID
    label: str
    creator: str
    short_description: str
    description: str
    project_id: uuid.UUID


@dataclass
class Tag:
    tag_id: uuid.UUID
    name: str
    count: int
