from typing import Annotated, TypedDict
import operator

def merge_lists(left: list, right: list) -> list:
    if left is None:
        left = []
    if right is None:
        right = []
    # If the elements are simple strings or dicts, concatenation is fine.
    # Duplicates will be handled in aggregator.
    return left + right

from langgraph.graph.message import add_messages

class ReviewState(TypedDict):
    pr_context: dict                          # Serialized PRContext
    messages: Annotated[list, add_messages]   # Agent conversation
    codebase_context: Annotated[list[str], merge_lists] # Retrieved from vector DB
    findings: Annotated[list[dict], merge_lists]        # Accumulated ReviewFinding dicts
    review_summary: str                       # Final formatted summary
    should_auto_fix: bool                     # Whether to trigger auto-fix
    fix_suggestions: Annotated[list[dict], merge_lists] # FixSuggestion dicts
    current_agent: str                        # Current active agent
    active_agents: Annotated[list[str], merge_lists]    # Which agents to run
    errors: Annotated[list[str], merge_lists] # Any agent errors
