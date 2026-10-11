import os
import json
import asyncio
import traceback
import httpx

from mcp.client.streamable_http import streamable_http_client
from mcp.client.session import ClientSession


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


RENDER_URL = os.environ.get(
    "MCP_SERVER_URL",
    "https://ai-job-finder-mcp.onrender.com/mcp"
)

LOCAL_PORTAL_TOOLS = {
    "search_linkedin": search_linkedin_jobs,
    "search_naukri": search_naukri_jobs,
    "search_indeed": search_indeed_jobs,
    "search_remoteok": search_remoteok_jobs,
    "search_weworkremotely": search_weworkremotely_jobs,
    "search_jobicy": search_jobicy_jobs,
    "search_arbeitnow": search_arbeitnow_jobs,
    "search_remotive": search_remotive_jobs,
}


_remote_healthy: bool = True


def call_remote_tool_sync(
    tool_name: str,
    query: str,
    location: str = ""
) -> list:
    """Call a remote MCP tool using Streamable HTTP, with automatic fallback to local scraper."""
    global _remote_healthy

    api_key = os.environ.get("MCP_API_KEY", "")
    disable_remote = os.environ.get("DISABLE_REMOTE_MCP", "").lower() in ["1", "true", "yes"]

    if api_key and _remote_healthy and not disable_remote:
        async def _run():
            headers = {"X-API-Key": api_key}

            try:
                async with httpx.AsyncClient(
                    headers=headers,
                    timeout=15.0  # Rapid timeout to avoid blocking on unresponsive/502 cloud services
                ) as http_client:

                    async with streamable_http_client(
                        RENDER_URL,
                        http_client=http_client
                    ) as (read_stream, write_stream):

                        async with ClientSession(
                            read_stream,
                            write_stream
                        ) as session:

                            await session.initialize()

                            response = await session.call_tool(
                                tool_name,
                                arguments={
                                    "query": query,
                                    "location": location
                                }
                            )

                            if getattr(response, "is_error", getattr(response, "isError", False)):
                                return []

                            if not response.content:
                                return []

                            text_output = response.content[0].text

                            try:
                                return json.loads(text_output)
                            except (json.JSONDecodeError, AttributeError):
                                return text_output

            except BaseException as e:
                err_msg = str(e)
                # Catch 502 Bad Gateway or connection failures and trip circuit breaker
                if "502" in err_msg or "Connection failed" in err_msg or "ConnectError" in err_msg:
                    print(f"[Remote MCP Status] Server unreachable or 502 ({err_msg}). Falling back to local scraper.")
                else:
                    print(f"[Remote MCP Status] Remote tool call failed: {e}. Falling back to local scraper.")
                return []

        try:
            results = asyncio.run(_run())
            if isinstance(results, list) and len(results) > 0:
                return results
            elif results == []:
                # If remote call returned empty or failed, consider remote unhealthy for this batch
                pass
        except BaseException as e:
            err_msg = str(e)
            if "502" in err_msg or "Connection failed" in err_msg:
                _remote_healthy = False
            print(f"[Remote MCP Status] Remote execution failed for {tool_name}: {e}. Using local scraper.")

    # Fallback to local scraping tools: directly scrapes RemoteOK, Remotive, Arbeitnow, Jobicy, etc.
    local_fn = LOCAL_PORTAL_TOOLS.get(tool_name)
    if local_fn:
        try:
            return local_fn(query=query, location=location)
        except BaseException as err:
            print(f"[Local Scraper Error] {tool_name} failed: {err}")
            return []

    return []


# Job-search tool wrappers

def search_linkedin(query: str, location: str = ""):
    return call_remote_tool_sync("search_linkedin", query, location)


def search_naukri(query: str, location: str = ""):
    return call_remote_tool_sync("search_naukri", query, location)


def search_indeed(query: str, location: str = ""):
    return call_remote_tool_sync("search_indeed", query, location)


def search_remoteok(query: str, location: str = ""):
    return call_remote_tool_sync("search_remoteok", query, location)


def search_weworkremotely(query: str, location: str = ""):
    return call_remote_tool_sync("search_weworkremotely", query, location)


def search_jobicy(query: str, location: str = ""):
    return call_remote_tool_sync("search_jobicy", query, location)


def search_arbeitnow(query: str, location: str = ""):
    return call_remote_tool_sync("search_arbeitnow", query, location)


def search_remotive(query: str, location: str = ""):
    return call_remote_tool_sync("search_remotive", query, location)