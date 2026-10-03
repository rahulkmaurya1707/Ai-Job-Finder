import logging
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import settings

logger = logging.getLogger(__name__)


def generate_cover_letter_draft(
    resume_summary: str,
    job_title: str,
    company_name: str,
    job_description: str,
) -> str:
    """Send candidate resume summary + job description to Groq asking for a short, structured cover letter draft."""
    try:
        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model="openai/gpt-oss-20b",
            temperature=0.3,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a professional career coach and expert resume writer. "
                    "Write a short, highly tailored, structured 3-paragraph cover letter draft for the candidate. "
                    "Structure:\n"
                    "1. Opening expressing enthusiasm for the specific role\n"
                    "2. Core matching skills and key relevant technical achievements\n"
                    "3. Confident closing & proactive call to action\n"
                    "Keep it professional, concise, direct, and ready for submission.",
                ),
                (
                    "user",
                    "Target Role: {job_title}\n"
                    "Company: {company_name}\n\n"
                    "Candidate Resume Summary:\n{resume_summary}\n\n"
                    "Job Description:\n{job_description}",
                ),
            ]
        )

        chain = prompt | llm
        response = chain.invoke(
            {
                "job_title": job_title,
                "company_name": company_name,
                "resume_summary": resume_summary,
                "job_description": job_description,
            }
        )
        return str(response.content).strip()
    except Exception as e:
        logger.warning(
            f"Failed to generate cover letter draft for {job_title} @ {company_name}: {e}"
        )
        return (
            f"Dear Hiring Team at {company_name},\n\n"
            f"I am writing to express my strong enthusiasm for the {job_title} position. "
            f"Given my background and technical skills, I am confident in my ability to add immediate value to your team.\n\n"
            f"Best regards,\nCandidate"
        )
