from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, Union, Literal
from datetime import datetime
from src.models.project import ProjectRoleEnum, ProjectStatusEnum, TaskStatusEnum


class TagDTO(BaseModel):
    tag_id: UUID
    name: str
    quantity_count: int = 0


class TaskDTO(BaseModel):
    task_id: UUID
    project_id: UUID
    creator_id: UUID
    label: str
    creator: str
    short_description: str
    description: str
    created_at: datetime
    updated_at: datetime
    answers_count: int = 0
    status: TaskStatusEnum


class TaskCreateDTO(BaseModel):
    label: str = Field(..., min_length=3, max_length=255)
    short_description: str = Field(..., max_length=500)
    description: str = Field(..., max_length=5000)


class TaskUpdateDTO(BaseModel):
    label: str = Field(..., min_length=3, max_length=255)
    short_description: str = Field(..., max_length=500)
    description: str = Field(..., max_length=5000)
    status: TaskStatusEnum = Field(...)


class PostDTO(BaseModel):
    post_id: UUID
    project_id: UUID
    creator_id: UUID
    label: str
    creator: str
    short_description: str
    description: str
    comments_count: int
    created_at: datetime
    updated_at: datetime


class PostCreateDTO(BaseModel):
    label: str = Field(..., min_length=3, max_length=255)
    short_description: str = Field(..., max_length=500)
    description: str = Field(..., max_length=5000)


class PostUpdateDTO(BaseModel):
    project_id: Optional[UUID] = None
    label: Optional[str] = Field(None, min_length=3, max_length=255)
    short_description: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)


class ProjectDTO(BaseModel):
    id: UUID
    label: str
    creator_id: UUID
    creator: str
    short_description: str
    description: str
    tags: list[TagDTO]
    created_at: datetime
    updated_at: datetime
    status: ProjectStatusEnum


class ProjectInfoDTO(BaseModel):
    project_id: UUID
    creator_id: UUID
    label: str
    creator: str
    description: str
    tags: list[TagDTO]
    created_at: datetime
    status: ProjectStatusEnum


class ProjectDetailDTO(ProjectDTO):
    activities: list[Union[TaskDTO, PostDTO]] = []


class ProjectCreateDTO(BaseModel):
    label: str = Field(..., min_length=3, max_length=255)
    short_description: str = Field(..., max_length=500)
    description: str = Field(..., max_length=5000)
    tags: list[str]
    status: ProjectStatusEnum = ProjectStatusEnum.ACTIVE


class ProjectUpdateDTO(BaseModel):
    label: str = Field(..., min_length=3, max_length=255)
    short_description: str = Field(..., max_length=500)
    description: str = Field(..., max_length=5000)
    tags: list[str]
    status: ProjectStatusEnum


class ProjectStatsDTO(BaseModel):
    project_id: UUID
    tasks_count: int
    participants_count: int
    answers_count: int


class PublicationDTO(BaseModel):
    id: UUID
    project_id: UUID
    label: str
    short_description: str
    created_at: datetime
    creator_id: UUID
    creator_name: str
    type: Literal["post", "task"]
    answers_count: int

    status: Optional[TaskStatusEnum] = None


class PublicationsResponse(BaseModel):
    items: list[PublicationDTO]
    next_cursor: Optional[str] = None
    has_more: bool = False


class MembershipProjectDTO(BaseModel):
    project_id: UUID
    label: str
    short_description: str
    created_at: datetime
    status: ProjectStatusEnum
    creator_name: str


class MembershipsDTO(BaseModel):
    scientist: list[MembershipProjectDTO]
    volunteer: list[MembershipProjectDTO]


class DenormUserDTO(BaseModel):
    id: UUID
    name: str = "unknown"
    role: ProjectRoleEnum
    avatar_link: str = ""
