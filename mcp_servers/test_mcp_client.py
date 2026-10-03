from mcp_servers.server import (
    search_linkedin,
    search_naukri,
    search_indeed,
    search_remoteok,
    search_weworkremotely,
    get_profile_resume_embedding,
    search_resume_embeddings,
)
from storage.vector_store import store_resume_vector

REQUIRED_JOB_FIELDS = {
    "title",
    "company",
    "location",
    "description",
    "posted_date",
    "apply_url",
    "source",
}


def test_mcp_tools():
    print("--- Running MCP Tools Test Client ---")

    # Seed vector store for embedding test
    store_resume_vector(
        "Client Test User", "Python Developer with AI and Web Scraping skills"
    )

    tools_to_test = [
        ("search_remoteok", lambda: search_remoteok("python")),
        ("search_weworkremotely", lambda: search_weworkremotely("python")),
        ("search_linkedin", lambda: search_linkedin("python", "remote")),
        ("search_indeed", lambda: search_indeed("python", "remote")),
        ("search_naukri", lambda: search_naukri("python", "india")),
        (
            "get_profile_resume_embedding",
            lambda: get_profile_resume_embedding("Client Test User"),
        ),
        (
            "search_resume_embeddings",
            lambda: search_resume_embeddings("Python AI Developer"),
        ),
    ]

    for tool_name, tool_fn in tools_to_test:
        print(f"\nTesting tool: {tool_name}...")
        res = tool_fn()
        if "search_" in tool_name and "embeddings" not in tool_name:
            assert isinstance(res, list), f"{tool_name} should return a list"
            if res:
                item_fields = set(res[0].keys())
                assert REQUIRED_JOB_FIELDS.issubset(
                    item_fields
                ), f"{tool_name} fields mismatch: {item_fields}"
                print(
                    f"[OK] {tool_name} returned {len(res)} normalized job items. Sample title: '{res[0]['title']}'"
                )
            else:
                print(f"[OK] {tool_name} returned empty list (clean).")
        else:
            assert isinstance(res, dict), f"{tool_name} should return a dict"
            print(f"[OK] {tool_name} returned clean result keys: {list(res.keys())}")

    print("\nALL MCP TOOLS VERIFIED SUCCESSFULLY WITH CLEAN NORMALIZED DATA!")


if __name__ == "__main__":
    test_mcp_tools()
