from app.agents.state import ReviewState
from app.config import get_settings

def aggregator_node(state: ReviewState) -> dict:
    findings = state.get("findings", [])
    settings = get_settings()
    
    # Deduplicate based on file, line, and similar description
    unique_findings = []
    seen = set()
    for f in findings:
        file_path = f.get("file_path") or f.get("file") or "unknown"
        line = f.get("start_line") or f.get("line") or 1
        category = f.get("category", "")
        desc_prefix = f.get("description", "")[:40]
        key = (file_path, line, category, desc_prefix)
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)
            
    # Sort by severity
    severity_order = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2, "INFO": 3}
    unique_findings.sort(key=lambda x: severity_order.get(x.get("severity", "INFO"), 4))
    
    has_critical_or_major = any(f.get("severity") in ("CRITICAL", "MAJOR") for f in unique_findings)
    verdict = "APPROVE"
    if has_critical_or_major:
        verdict = "REQUEST_CHANGES"
    elif unique_findings:
        verdict = "COMMENT"
        
    has_fixable = any(f.get("auto_fixable") for f in unique_findings)
    # If config allows auto fix and there are fixable findings
    should_auto_fix = getattr(settings, "auto_fix_enabled", True) and has_fixable
    
    summary_lines = [f"# Code Review Result: {verdict}"]
    summary_lines.append(f"Total findings: {len(unique_findings)}\n")
    for f in unique_findings:
        f_file = f.get("file_path") or f.get("file") or "unknown"
        f_line = f.get("start_line") or f.get("line") or ""
        summary_lines.append(f"- **[{f.get('severity', 'INFO')}]** {f_file}:{f_line} - {f.get('description', '')}")
        
    review_summary = "\n".join(summary_lines)
    
    return {
        "review_summary": review_summary,
        "should_auto_fix": should_auto_fix
    }
