from typing import List, Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    name: str
    skills: List[str] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    experience_years: float = 0.0
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    locations: List[str] = Field(default_factory=list)
    remote_ok: bool = True
    raw_resume_text: Optional[str] = None
