from mcp.server import MCPServer
from mcp_servers.portal_tools import (
    search_linkedin_jobs,
    search_naukri_jobs,
    search_indeed_jobs,
    search_remoteok_jobs,
    search_weworkremotely_jobs,
    search_jobicy_jobs,
    search_arbeitnow_jobs,
    search_remotive_jobs,
)
from storage.vector_store import (
    get_resume_embedding_by_user,
    search_resume_vector_store,
)
from mcp_servers.notification_tool import send_notification

# Initialize MCPServer instance using official Python MCP SDK
mcp = MCPServer("JobFinderServer")


@mcp.tool()
def search_linkedin(query: str, location: str = "") -> list:
    """Search for jobs on LinkedIn."""
    return search_linkedin_jobs(query, location)


@mcp.tool()
def search_naukri(query: str, location: str = "") -> list:
    """Search for jobs on Naukri."""
    return search_naukri_jobs(query, location)


@mcp.tool()
def search_indeed(query: str, location: str = "") -> list:
    """Search for jobs on Indeed."""
    return search_indeed_jobs(query, location)


@mcp.tool()
def search_remoteok(query: str, location: str = "") -> list:
    """Search for jobs on RemoteOK."""
    return search_remoteok_jobs(query, location)


@mcp.tool()
def search_weworkremotely(query: str, location: str = "") -> list:
    """Search for jobs on WeWorkRemotely."""
    return search_weworkremotely_jobs(query, location)


@mcp.tool()
def search_jobicy(query: str, location: str = "") -> list:
    """Search for remote tech jobs on Jobicy."""
    return search_jobicy_jobs(query, location)


@mcp.tool()
def search_arbeitnow(query: str, location: str = "") -> list:
    """Search for tech jobs on Arbeitnow."""
    return search_arbeitnow_jobs(query, location)


@mcp.tool()
def search_remotive(query: str, location: str = "") -> list:
    """Search for remote jobs on Remotive."""
    return search_remotive_jobs(query, location)


@mcp.tool()
def get_profile_resume_embedding(user_name: str = "Candidate") -> dict:
    """Query Chroma vector store for the current profile's resume embedding."""
    return get_resume_embedding_by_user(user_name)


@mcp.tool()
def search_resume_embeddings(query_text: str = "ping", n_results: int = 3) -> dict:
    """Query Chroma vector store for matching resume chunks."""
    results = search_resume_vector_store(query_text=query_text or "ping", n_results=n_results)
    return {"results": results}


@mcp.tool()
def send_notification_tool(
    message: str,
    subject: str = "Job Finder Shortlist Notification",
    is_ping: bool = False,
) -> dict:
    """Send job shortlist notification via Telegram Bot API or SMTP Email."""
    return send_notification(message=message, subject=subject, is_ping=is_ping)


if __name__ == "__main__":
    import os
    import hmac
    import uvicorn
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    api_key = os.environ.get("MCP_API_KEY")
    if not api_key:
        raise RuntimeError("MCP_API_KEY environment variable is required")

    class APIKeyMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            supplied_key = request.headers.get("X-API-Key", "")
            if not hmac.compare_digest(supplied_key, api_key):
                return JSONResponse(
                    {"error": "Unauthorized"},
                    status_code=401,
                )
            return await call_next(request)

    app = mcp.streamable_http_app(host="0.0.0.0")
    app.add_middleware(APIKeyMiddleware)

    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run(app, host="0.0.0.0", port=port)