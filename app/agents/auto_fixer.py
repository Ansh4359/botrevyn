from app.agents.state import ReviewState
from app.config import get_settings
from langchain_core.messages import SystemMessage, HumanMessage
import json
from app.agents.helpers import extract_json_array

def auto_fixer_node(state: ReviewState) -> dict:
    should_auto_fix = state.get("should_auto_fix", False)
    if not should_auto_fix:
        return {"fix_suggestions": []}
        
    findings = state.get("findings", [])
    fixable_findings = [f for f in findings if f.get("auto_fixable")]
    
    if not fixable_findings:
        return {"fix_suggestions": []}
        
    settings = get_settings()
    llm = settings.get_llm()
    
    system_prompt = (
        "You are an automated code fixer. You will be provided with a file path, its current content or diff snippet, "
        "and a finding description that needs to be fixed. "
        "Generate a fix for the issue. Respond strictly with a JSON object containing: "
        "'file', 'original_code' (the snippet to replace), 'fixed_code' (the replacement snippet)."
    )
    
    fix_suggestions = []
    
    # Limit to top 3 fixable items to prevent LLM quota exhaustion
    for finding in fixable_findings[:3]:
        file_name = finding.get("file_path") or finding.get("file")
        line_no = finding.get("start_line") or finding.get("line")
        desc = finding.get("description", "")
        human_prompt = f"File: {file_name}\nLine: {line_no}\nIssue: {desc}\nGenerate JSON fix."
        try:
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ])
            content = response.content
            if isinstance(content, list):
                content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
            elif not isinstance(content, str):
                content = str(content)
                
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != 0:
                fix_data = json.loads(content[start:end])
                fix_suggestions.append(fix_data)
        except Exception:
            pass
            
    return {"fix_suggestions": fix_suggestions}
