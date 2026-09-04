from app.agents.state import ReviewState
from app.agents.helpers import _build_review_prompt, extract_json_array
from app.config import get_settings
from langchain_core.messages import SystemMessage, HumanMessage

def test_coverage_node(state: ReviewState) -> dict:
    active = state.get("active_agents", [])
    if active and "test_coverage" not in active:
        return {}

    pr_context = state.get("pr_context", {})
    codebase_context = state.get("codebase_context", [])
    
    settings = get_settings()
    llm = settings.get_llm()
    
    system_prompt = (
        "You are a Test Engineering expert. Identify new or modified functions and classes in the PR diff. "
        "Check if corresponding tests exist. Suggest test cases for untested code. "
        "Respond strictly with a JSON array of findings. Each finding must be an object with keys: "
        "'file', 'line' (integer or null), 'description' (include suggested test stubs), 'severity' (CRITICAL, MAJOR, MINOR, INFO), "
        "'category' (TEST_COVERAGE), 'auto_fixable' (boolean)."
    )
    
    human_prompt = _build_review_prompt(pr_context, codebase_context)
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        
        findings = extract_json_array(response.content)
        return {"findings": findings}
    except Exception as e:
        return {"errors": [f"test_coverage_node error: {str(e)}"]}
