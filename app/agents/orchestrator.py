from app.agents.state import ReviewState

def orchestrator_node(state: ReviewState) -> dict:
    pr_context = state.get("pr_context", {})
    files = pr_context.get("files", [])
    
    active_agents = ["code_quality"]
    
    has_code = False
    has_tests = False
    has_docs = False
    
    code_extensions = (
        ".py", ".ipynb", ".js", ".jsx", ".ts", ".tsx",
        ".go", ".java", ".cpp", ".c", ".rs", ".rb",
        ".php", ".sh", ".sql", ".yaml", ".yml", ".json"
    )
    for f in files:
        filename = f.get("filename", "").lower()
        if filename.endswith(code_extensions):
            has_code = True
            if "test" in filename:
                has_tests = True
        if filename.endswith((".md", ".rst", ".txt")) or "docs" in filename:
            has_docs = True
            
    if has_code:
        if "security" not in active_agents:
            active_agents.append("security")
        if "style_convention" not in active_agents:
            active_agents.append("style_convention")
            
    if has_tests or has_code:
        if "test_coverage" not in active_agents:
            active_agents.append("test_coverage")
            
    if has_docs or has_code:
        if "documentation" not in active_agents:
            active_agents.append("documentation")
            
    codebase_context = []
    # Here you would typically retrieve from ChromaDB using PR keywords
    # For now, we handle gracefully if DB is not indexed yet
    
    return {
        "active_agents": active_agents,
        "codebase_context": codebase_context
    }
