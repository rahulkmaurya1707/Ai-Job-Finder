from langchain_groq import ChatGroq
from config import settings
print(ChatGroq(api_key=settings.GROQ_API_KEY, model="openai/gpt-oss-20b").invoke("hello").content)
