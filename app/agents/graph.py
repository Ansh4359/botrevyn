"""LangGraph StateGraph definition for the multi-agent review workflow.

Flow:
  START → orchestrator → [parallel fan-out to active agents] → aggregator
  → conditional: auto_fixer or END
"""

from datetime import datetime, timezone
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from app.agents.state import ReviewState
logger = logging.getLogger(__name__)

from app.agents.orchestrator import orchestrator_node
from app.agents.code_quality import code_quality_node
from app.agents.security import security_node
from app.agents.test_coverage import test_coverage_node
from app.agents.style_convention import style_convention_node
from app.agents.documentation import documentation_node
from app.agents.aggregator import aggregator_node
from app.agents.auto_fixer import auto_fixer_node
from app.models.pr_context import PRContext
from app.models.review import ReviewResult, ReviewFinding, FixSuggestion, Severity, ReviewCategory


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

def route_to_agents(state: ReviewState) -> list[Send]:
    """Fan-out: dispatch to each active review agent in parallel."""
    agent_map = {
        "code_quality": "code_quality",
        "security": "security",
        "test_coverage": "test_coverage",
        "style_convention": "style_convention",
        "documentation": "documentation",
    }
    return [
        Send(agent_map[agent], state)
        for agent in state.get("active_agents", [])
        if agent in agent_map
    ]


def route_after_aggregator(state: ReviewState) -> str:
    """Conditional edge: go to auto_fixer if enabled, otherwise END."""
    if state.get("should_auto_fix"):
        return "auto_fixer"
    return END


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

workflow = StateGraph(ReviewState)

workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("code_quality", code_quality_node)
workflow.add_node("security", security_node)
workflow.add_node("test_coverage", test_coverage_node)
workflow.add_node("style_convention", style_convention_node)
workflow.add_node("documentation", documentation_node)
workflow.add_node("aggregator", aggregator_node)
workflow.add_node("auto_fixer", auto_fixer_node)

workflow.add_edge(START, "orchestrator")
workflow.add_edge("orchestrator", "code_quality")
workflow.add_edge("code_quality", "security")
workflow.add_edge("security", "style_convention")
workflow.add_edge("style_convention", "test_coverage")
workflow.add_edge("test_coverage", "documentation")
workflow.add_edge("documentation", "aggregator")

workflow.add_conditional_edges(
    "aggregator",
    route_after_aggregator,
    ["auto_fixer", END],
)
workflow.add_edge("auto_fixer", END)

review_graph = workflow.compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def _serialize_pr_context(pr_context: PRContext) -> dict:
    """Convert PRContext into a plain dict the agents can read from state."""
    return {
        "repo_full_name": pr_context.repo_full_name,
        "pr_number": pr_context.pr_number,
        "title": pr_context.title,
        "description": pr_context.body,
        "author": pr_context.author.login if pr_context.author else "unknown",
        "base_branch": pr_context.base_branch,
        "head_branch": pr_context.head_branch,
        "head_sha": pr_context.head_sha,
        "labels": pr_context.labels,
        "files": [
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "patch": f.patch or "",
            }
            for f in pr_context.diff_files
        ],
        "file_contents": [
            {
                "path": fc.path,
                "content": fc.content,
                "language": fc.language,
            }
            for fc in pr_context.file_contents
        ],
    }


def run_review(pr_context: PRContext) -> ReviewResult:
    """Run the full multi-agent review pipeline and return a ReviewResult."""
    initial_state: ReviewState = {
        "pr_context": _serialize_pr_context(pr_context),
        "messages": [],
        "codebase_context": [],
        "findings": [],
        "review_summary": "",
        "should_auto_fix": False,
        "fix_suggestions": [],
        "active_agents": [],
        "errors": [],
    }

    result_state = review_graph.invoke(initial_state)

    # Convert raw finding dicts back to Pydantic models
    raw_findings = result_state.get("findings", [])
    logger.info(f"Raw findings from graph state: {len(raw_findings)}")
    findings = []
    seen = set()
    for f in raw_findings:
        if not isinstance(f, dict):
            continue
        try:
            file_path = f.get("file_path") or f.get("file") or "unknown"
            line = f.get("start_line") or f.get("line") or 1
            start_line = int(line) if line else 1
            end_line = int(f.get("end_line") or start_line)
            title = f.get("title") or (f.get("description", "Code Issue")[:60])
            description = f.get("description", "")
            
            # Severity mapping
            sev_str = str(f.get("severity", "INFO")).upper()
            if sev_str not in ("CRITICAL", "MAJOR", "MINOR", "SUGGESTION", "INFO"):
                sev_str = "INFO"
                
            # Category mapping
            cat_str = str(f.get("category", "CODE_QUALITY")).upper()
            if cat_str not in ("CODE_QUALITY", "SECURITY", "TEST_COVERAGE", "STYLE", "DOCUMENTATION", "PERFORMANCE"):
                cat_str = "CODE_QUALITY"

            # Deduplicate by file, line, and first 40 chars of description
            dedup_key = (file_path, start_line, description[:40])
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            finding = ReviewFinding(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                title=title,
                description=description,
                severity=Severity(sev_str),
                category=ReviewCategory(cat_str),
                suggestion=f.get("suggestion"),
                code_snippet=f.get("code_snippet"),
                auto_fixable=bool(f.get("auto_fixable", False)),
            )
            findings.append(finding)
        except Exception as e:
            logger.warning(f"Error parsing finding {f}: {e}")

    logger.info(f"Final parsed ReviewFinding count: {len(findings)}")

    fix_suggestions = []
    for f in result_state.get("fix_suggestions", []):
        try:
            fix_suggestions.append(FixSuggestion(**f))
        except Exception:
            pass

    # Determine verdict
    has_critical = any(f.severity.value in ("CRITICAL", "MAJOR") for f in findings)
    verdict = "REQUEST_CHANGES" if has_critical else ("APPROVE" if not findings else "COMMENT")

    return ReviewResult(
        pr_number=pr_context.pr_number,
        repo_full_name=pr_context.repo_full_name,
        findings=findings,
        summary=result_state.get("review_summary", ""),
        overall_verdict=verdict,
        fix_suggestions=fix_suggestions,
        reviewed_at=datetime.now(timezone.utc),
        review_duration_seconds=0.0,  # caller fills in the real duration
    )
