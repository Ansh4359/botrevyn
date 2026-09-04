from app.agents.state import ReviewState
from app.agents.helpers import _build_review_prompt, extract_json_array
from app.config import get_settings
from langchain_core.messages import SystemMessage, HumanMessage

def code_quality_node(state: ReviewState) -> dict:
    active = state.get("active_agents", [])
    if active and "code_quality" not in active:
        return {}

    pr_context = state.get("pr_context", {})
    codebase_context = state.get("codebase_context", [])
    
    settings = get_settings()
    llm = settings.get_llm()
    
    system_prompt = (
        "You are an expert code reviewer focused on bugs, logic errors, syntax errors, performance issues, and broken code. "
        "Carefully inspect the git diff for each file. If you find syntax errors, invalid statements (e.g. broken list comprehensions, unclosed brackets), "
        "undefined variables, or bugs, report them. "
        "Respond strictly with a JSON array of findings. Each finding must be an object with keys: "
        "'file_path' (string, path of the file), 'start_line' (integer, line number), 'title' (short summary), "
        "'description' (clear explanation of the bug and how to fix it), 'severity' (CRITICAL, MAJOR, MINOR, INFO), "
        "'category' (CODE_QUALITY), 'auto_fixable' (boolean)."
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
        return {"errors": [f"code_quality_node error: {str(e)}"]}
