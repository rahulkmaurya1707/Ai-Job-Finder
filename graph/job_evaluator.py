from enum import Enum
from typing import List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import settings


class RecommendationEnum(str, Enum):
    APPLY = "Apply"
    CONSIDER = "Consider"
    SKIP = "Skip"


class JobMatchEvaluation(BaseModel):
    match_score: int = Field(
        ge=0, le=100, description="Overall match score from 0 to 100"
    )
    matching_skills: List[str] = Field(
        default_factory=list,
        description="List of candidate skills matching job requirements",
    )
    missing_skills: List[str] = Field(
        default_factory=list,
        description="List of candidate skills missing or weak for job requirements",
    )
    recommendation: RecommendationEnum = Field(
        description="Recommendation enum value: 'Apply', 'Consider', or 'Skip'"
    )
    one_line_reasoning: str = Field(
        description="Concise one-line explanation of the evaluation result"
    )


def evaluate_job_match(
    resume_summary: str, job_description: str
) -> JobMatchEvaluation:
    """Send resume summary and job description to Groq via LangChain for structured match evaluation with Enum values."""
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="openai/gpt-oss-20b",
        temperature=0.0,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert HR AI evaluator. "
                "Analyze the candidate's resume summary against the job description. "
                "Return a structured evaluation JSON bound to the specified Pydantic schema. "
                "The recommendation MUST be strictly one of these enum strings: 'Apply', 'Consider', or 'Skip'.",
            ),
            (
                "user",
                "Candidate Resume Summary:\n{resume_summary}\n\n"
                "Job Description:\n{job_description}",
            ),
        ]
    )

    structured_llm = llm.with_structured_output(JobMatchEvaluation)
    chain = prompt | structured_llm

    truncated_desc = job_description[:1200] if job_description else ""
    return chain.invoke(
        {"resume_summary": resume_summary, "job_description": truncated_desc}
    )
