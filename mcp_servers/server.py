from mcp.server import MCPServer
from mcp_servers.portal_tools import (
    search_linkedin_jobs,
    search_naukri_jobs,
    search_indeed_jobs,
    search_remoteok_jobs,
    search_weworkremotely_jobs,
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
def get_profile_resume_embedding(user_name: str) -> dict:
    """Query Chroma vector store for the current profile's resume embedding."""
    return get_resume_embedding_by_user(user_name)


@mcp.tool()
def send_notification_tool(
    message: str,
    subject: str = "Job Finder Shortlist Notification",
    is_ping: bool = False,
) -> dict:
    """Send job shortlist notification via Telegram Bot API or SMTP Email."""
    return send_notification(message=message, subject=subject, is_ping=is_ping)


if __name__ == "__main__":
    mcp.run()
