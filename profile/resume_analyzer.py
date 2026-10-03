from typing import List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import settings


class StructuredResumeData(BaseModel):
    candidate_name: str = Field(
        default="", description="Full name of the candidate extracted from the resume header"
    )
    skills: List[str] = Field(
        default_factory=list,
        description="Extracted technical and professional skills",
    )
    experience_years: float = Field(
        default=0.0, description="Total estimated years of professional work experience"
    )
    preferred_roles: List[str] = Field(
        default_factory=list, description="List of target/preferred job titles or roles"
    )
    locations: List[str] = Field(
        default_factory=list, description="Extracted candidate locations or cities"
    )
    education: List[str] = Field(
        default_factory=list,
        description="Degrees, certifications, or educational qualifications",
    )


def analyze_resume_text(resume_text: str) -> StructuredResumeData:
    """Send raw resume text to Groq via LangChain and extract structured JSON output."""
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="openai/gpt-oss-20b",
        temperature=0.0,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert HR resume parser. Extract candidate full name, technical skills, preferred roles, estimated experience years, and locations from the resume text accurately.",
            ),
            ("user", "Resume Text:\n\n{resume_text}"),
        ]
    )

    structured_llm = llm.with_structured_output(StructuredResumeData)
    chain = prompt | structured_llm

    return chain.invoke({"resume_text": resume_text})
