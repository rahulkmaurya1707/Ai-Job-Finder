import asyncio
from typing import Dict, Any
from mcp_servers.server import mcp
from config import get_logger

logger = get_logger(__name__)

PING_KWARGS = {
    "search_linkedin": {"query": "ping", "location": "Remote"},
    "search_naukri": {"query": "ping", "location": "Remote"},
    "search_indeed": {"query": "ping", "location": "Remote"},
    "search_remoteok": {"query": "ping", "location": "Remote"},
    "search_weworkremotely": {"query": "ping", "location": "Remote"},
    "get_profile_resume_embedding": {"user_name": "ping_test"},
    "send_notification_tool": {"message": "ping", "subject": "ping", "is_ping": True},
}


async def _ping_single_tool(
    tool_name: str,
    timeout_seconds: float = 8.0,
    max_attempts: int = 2,
    delay_seconds: float = 1.0,
) -> Dict[str, Any]:
    """Ping an individual MCP tool by name with retry (up to max_attempts) & timeout."""
    kwargs = PING_KWARGS.get(tool_name, {})
    last_reason = "Unknown error"

    for attempt in range(1, max_attempts + 1):
        try:
            res = await asyncio.wait_for(
                mcp.call_tool(tool_name, kwargs), timeout=timeout_seconds
            )
            if isinstance(res, dict) and res.get("error"):
                last_reason = str(res.get("error"))
            else:
                return {"name": tool_name, "reachable": True, "reason": "OK"}
        except asyncio.TimeoutError:
            last_reason = f"Timed out after {timeout_seconds}s"
        except Exception as e:
            last_reason = str(e)

        if attempt < max_attempts:
            logger.info(
                f"Tool '{tool_name}' ping attempt {attempt}/{max_attempts} failed ({last_reason}). Retrying in {delay_seconds}s..."
            )
            await asyncio.sleep(delay_seconds)

    return {
        "name": tool_name,
        "reachable": False,
        "reason": f"Failed after {max_attempts} attempts ({last_reason})",
    }


async def ping_mcp_tools_async(timeout_per_tool: float = 8.0) -> Dict[str, Dict[str, Any]]:
    """Asynchronously ping each registered MCP tool and log any that are unreachable."""
    tools = await mcp.list_tools()
    tasks = [_ping_single_tool(t.name, timeout_seconds=timeout_per_tool) for t in tools]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    status_summary = {}
    unreachable_tools = []

    for item in results_list:
        if isinstance(item, dict):
            name = item["name"]
            is_reachable = item["reachable"]
            reason = item["reason"]
            status_summary[name] = {"reachable": is_reachable, "reason": reason}
            if not is_reachable:
                unreachable_tools.append((name, reason))
        elif isinstance(item, Exception):
            logger.warning(f"[MCP PING ERROR] Ping task exception: {item}")

    logger.info("=== MCP TOOLS HEALTH CHECK (PRE-RUN PING) ===")
    for name, info in status_summary.items():
        status_str = "REACHABLE" if info["reachable"] else f"UNREACHABLE ({info['reason']})"
        icon = "[OK]" if info["reachable"] else "[WARNING]"
        logger.info(f"  {icon} {name:<30} -> {status_str}")

    if unreachable_tools:
        unreachable_names = [name for name, _ in unreachable_tools]
        msg = f"[MCP PING WARNING] {len(unreachable_tools)} MCP tool(s) UNREACHABLE: {', '.join(unreachable_names)}"
        logger.warning(msg)
    else:
        msg = "[MCP PING SUCCESS] All MCP tools are healthy and reachable."
        logger.info(msg)

    return status_summary


def ping_mcp_tools(timeout_per_tool: float = 8.0) -> Dict[str, Dict[str, Any]]:
    """Synchronous entry point to ping each MCP tool briefly before a full run and log unreachable tools."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Handle case where event loop is already running
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(ping_mcp_tools_async(timeout_per_tool=timeout_per_tool))
    else:
        return asyncio.run(ping_mcp_tools_async(timeout_per_tool=timeout_per_tool))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ping_mcp_tools()
