from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, List
from datetime import datetime

class TagDTO(BaseModel):
    id: UUID
    name: str
    
    class Config:
        from_attributes = True

class TaskDTO(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str
    requirements: Optional[str]
    created_at: datetime
    answers_count: int = 0
    
    class Config:
        from_attributes = True

class ProjectDTO(BaseModel):
    id: UUID
    title: str
    description: str
    short_description: str
    tags: List[TagDTO]
    author_id: UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool

class ProjectDetailDTO(ProjectDTO):
    tasks: List[TaskDTO]

class ProjectCreateDTO(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str
    short_description: str = Field(..., max_length=300)
    tags: List[str]
    is_active: bool = True

class ProjectUpdateDTO(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

class ReportDTO(BaseModel):
    id: UUID
    task_id: UUID
    user_id: UUID
    content: str
    media_ids: List[UUID] = []
    status: str = "pending"  # pending/approved/rejected
    created_at: datetime
    
    class Config:
        from_attributes = True

class ReportCreateDTO(BaseModel):
    task_id: UUID
    content: str
    media_ids: List[UUID] = []

class ReportReviewDTO(BaseModel):
    status: str  # approved/rejected
    comment: Optional[str] = None

class ProjectStatsDTO(BaseModel):
    project_id: UUID
    tasks_count: int
    participants_count: int
    answers_count: int