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


def call_remote_tool_sync(
    tool_name: str,
    query: str,
    location: str = ""
) -> list:
    """Call a remote MCP tool using Streamable HTTP, with automatic fallback to local scraper."""

    api_key = os.environ.get("MCP_API_KEY", "")

    if api_key:
        async def _run():
            headers = {"X-API-Key": api_key}

            try:
                async with httpx.AsyncClient(
                    headers=headers,
                    timeout=120.0
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
                                print(
                                    f"[Remote MCP Error] Tool failed: {tool_name}"
                                )
                                return []

                            if not response.content:
                                return []

                            text_output = response.content[0].text

                            try:
                                return json.loads(text_output)
                            except (json.JSONDecodeError, AttributeError):
                                return text_output

            except Exception as e:
                print(f"[Remote MCP Error] Failed to call {tool_name}: {e}")
                traceback.print_exc()
                # If wrapped inside ExceptionGroup or TaskGroup, unpack sub-exceptions
                if hasattr(e, "exceptions"):
                    for idx, sub_exc in enumerate(e.exceptions, start=1):
                        print(f"--- Sub-exception {idx} for {tool_name}: {sub_exc} ---")
                        traceback.print_exception(type(sub_exc), sub_exc, sub_exc.__traceback__)
                return []

        try:
            results = asyncio.run(_run())
            if isinstance(results, list) and len(results) > 0:
                return results
        except Exception as e:
            print(f"[Remote MCP Error] Execution failed for {tool_name}: {e}")

    # Fallback to local scraping tools if remote call is unconfigured, unreachable, or returned no data
    local_fn = LOCAL_PORTAL_TOOLS.get(tool_name)
    if local_fn:
        try:
            return local_fn(query=query, location=location)
        except Exception as err:
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