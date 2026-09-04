import json

def _build_review_prompt(pr_context: dict, codebase_context: list[str]) -> str:
    prompt = f"PR Title: {pr_context.get('title', 'N/A')}\n"
    prompt += f"PR Description: {pr_context.get('description', 'N/A')}\n\n"
    
    if codebase_context:
        prompt += "Codebase Context:\n"
        for ctx in codebase_context:
            prompt += f"- {ctx}\n"
        prompt += "\n"
        
    prompt += "Changed Files:\n"
    for f in pr_context.get("files", []):
        patch = f.get("patch", "")
        if len(patch) > 120000:
            patch = patch[:120000] + "\n... [diff truncated for length] ...\n"
        prompt += f"File: {f.get('filename')} (Status: {f.get('status')})\n"
        prompt += f"Diff:\n{patch}\n\n"
        
    return prompt

from typing import Any

def extract_json_array(text: Any) -> list[dict]:
    if isinstance(text, list):
        parts = []
        for item in text:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item))
        text = "\n".join(parts)
    elif not isinstance(text, str):
        text = str(text)

    try:
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != 0:
            return json.loads(text[start:end])
    except Exception:
        pass
    return []
