from typing import List, Dict, Any, Optional, TypedDict
from pydantic import BaseModel, Field
from profile.user_profile import UserProfile


class GraphState(TypedDict, total=False):
    """LangGraph State object with required pipeline stage fields."""
    profile: Optional[UserProfile]
    raw_postings: List[Dict[str, Any]]
    deduped_postings: List[Dict[str, Any]]
    filtered_postings: List[Dict[str, Any]]
    scored_postings: List[Dict[str, Any]]
    shortlist: List[Dict[str, Any]]
    resume_summary: Optional[str]
    run_id: Optional[str]
    widened_criteria: bool


class JobFinderStateModel(BaseModel):
    """Pydantic equivalent model for GraphState validation."""
    profile: Optional[UserProfile] = None
    raw_postings: List[Dict[str, Any]] = Field(default_factory=list)
    deduped_postings: List[Dict[str, Any]] = Field(default_factory=list)
    filtered_postings: List[Dict[str, Any]] = Field(default_factory=list)
    scored_postings: List[Dict[str, Any]] = Field(default_factory=list)
    shortlist: List[Dict[str, Any]] = Field(default_factory=list)
    resume_summary: Optional[str] = None
    run_id: Optional[str] = None
    widened_criteria: bool = False
