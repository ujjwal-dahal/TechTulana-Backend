
from langgraph.graph import StateGraph, START, END

from app.graph.state import GraphState

from app.graph.nodes import (
    parse_node,
    select_sites_node,
    extract_node,
    retry_extract_node,
    validate_node,
    compare_node,
    route_after_parse,
    route_after_select,
    route_after_extract,
)


def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("parse", parse_node)
    builder.add_node("select_sites", select_sites_node)
    builder.add_node("extract", extract_node)
    builder.add_node("retry_extract", retry_extract_node)
    builder.add_node("validate", validate_node)
    builder.add_node("compare", compare_node)

    builder.add_edge(START, "parse")

    builder.add_conditional_edges(
        "parse",
        route_after_parse,
    )

    builder.add_conditional_edges(
        "select_sites",
        route_after_select,
    )

    builder.add_conditional_edges(
        "extract",
        route_after_extract,
        {
            "retry_extract": "retry_extract",
            "validate": "validate",
        },
    )

    builder.add_conditional_edges(
        "retry_extract",
        route_after_extract,
        {
            "retry_extract": "retry_extract",
            "validate": "validate",
        },
    )

    builder.add_edge("validate", "compare")
    builder.add_edge("compare", END)

    return builder.compile()


graph = build_graph()
