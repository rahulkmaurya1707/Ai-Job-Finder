import os
import json
import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

RENDER_URL = "https://ai-job-finder-mcp.onrender.com/sse"

def call_remote_tool_sync(tool_name: str, query: str, location: str) -> list:
    """Creates a temporary event loop to securely call the Render MCP backend via SSE."""
    async def _run():
        api_key = os.environ.get("MCP_API_KEY", "")
        headers = {"X-API-Key": api_key}
        
        try:
            async with sse_client(url=RENDER_URL, headers=headers) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    response = await session.call_tool(
                        tool_name, 
                        arguments={"query": query, "location": location}
                    )
                    
                    if not response.content:
                        return []
                    
                    text_output = response.content[0].text
                    try:
                        return json.loads(text_output)
                    except json.JSONDecodeError:
                        return text_output
        except Exception as e:
            print(f"[Remote MCP Error] Failed to call {tool_name}: {e}")
            return []

    return asyncio.run(_run())


# --- Drop-in replacements for graph/nodes.py ---

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