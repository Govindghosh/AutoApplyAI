from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

class ResumeBase(BaseModel):
    name: str
    content_text: str
    file_path: Optional[str] = None
    is_base: bool = False

class ResumeCreate(ResumeBase):
    pass

class ResumeResponse(ResumeBase):
    id: int
    profile_id: int
    version: int
    is_optimized: bool
    extraction_status: str
    extraction_data: Optional[Dict[str, Any]] = None
    confidence_scores: Optional[Dict[str, float]] = None
    review_status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ResumeApproveRequest(BaseModel):
    approved_fields: List[str] # List of fields to sync: ["full_name", "skills"]

class UserProfileBase(BaseModel):
    full_name: Optional[str] = None
    title: Optional[str] = None
    experience_years: Optional[int] = None
    skills: List[str] = Field(default_factory=list)
    tech_stack: Dict[str, List[str]] = Field(default_factory=dict)
    preferred_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    remote_preference: str = "Remote"
    salary_expectation: Optional[int] = None
    preferred_currency: str = "USD"
    work_authorization: Optional[str] = None
    bio: Optional[str] = None
    locked_fields: List[str] = Field(default_factory=list)

    @field_validator("skills", "preferred_roles", "preferred_locations", "locked_fields", mode="before")
    @classmethod
    def default_list(cls, value):
        return [] if value is None else value

    @field_validator("tech_stack", mode="before")
    @classmethod
    def default_dict(cls, value):
        return {} if value is None else value

    @field_validator("remote_preference", mode="before")
    @classmethod
    def default_remote_preference(cls, value):
        return "Remote" if value is None else value

    @field_validator("preferred_currency", mode="before")
    @classmethod
    def default_preferred_currency(cls, value):
        return "USD" if value is None else value

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int
    resumes: List[ResumeResponse] = Field(default_factory=list)
    salary_multi_currency: Dict[str, float] = Field(default_factory=dict)
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
