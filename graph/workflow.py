from langgraph.graph import StateGraph, END
from graph.state import GraphState
from graph.nodes import (
    load_profile_node,
    search_sources_node,
    dedupe_node,
    filter_node,
    widen_criteria_node,
    route_after_filter,
    match_score_node,
    rank_node,
    present_node,
    notify_node,
)


def create_job_finder_graph():
    """Build and compile LangGraph StateGraph pipeline with conditional criteria widening fallback."""
    builder = StateGraph(GraphState)

    # 1. Add nodes
    builder.add_node("load_profile", load_profile_node)
    builder.add_node("search_sources", search_sources_node)
    builder.add_node("dedupe", dedupe_node)
    builder.add_node("filter", filter_node)
    builder.add_node("widen_criteria", widen_criteria_node)
    builder.add_node("match_score", match_score_node)
    builder.add_node("rank", rank_node)
    builder.add_node("present", present_node)
    builder.add_node("notify", notify_node)

    # 2. Add sequential edges & conditional retry edge
    builder.set_entry_point("load_profile")
    builder.add_edge("load_profile", "search_sources")
    builder.add_edge("search_sources", "dedupe")
    builder.add_edge("dedupe", "filter")

    # Conditional edge after filter: if 0 jobs survive, route to widen_criteria once; else match_score
    builder.add_conditional_edges(
        "filter",
        route_after_filter,
        {
            "widen_criteria": "widen_criteria",
            "match_score": "match_score",
        },
    )

    # Loop back from widen_criteria to retry filter node
    builder.add_edge("widen_criteria", "filter")

    builder.add_edge("match_score", "rank")
    builder.add_edge("rank", "present")
    builder.add_edge("present", "notify")
    builder.add_edge("notify", END)

    return builder.compile()


app_graph = create_job_finder_graph()
