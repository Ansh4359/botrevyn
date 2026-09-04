from typing import List, Optional, Dict
from app.models.pr_context import FileContent, PRContext
from app.tools.code_analyzer import extract_functions, extract_classes, extract_imports, detect_language

def get_surrounding_context(content: str, line: int, window: int = 10) -> str:
    lines = content.splitlines()
    start = max(0, line - 1 - window)
    end = min(len(lines), line + window)
    return "\n".join(lines[start:end])

def resolve_imports_context(file_content: FileContent, pr_context: PRContext) -> List[str]:
    lang = detect_language(file_content.filename)
    imports = extract_imports(file_content.content, lang)
    
    related_files = []
    for imp in imports:
        words = imp.replace(".", " ").replace("/", " ").split()
        for pr_file in pr_context.files:
            if pr_file.filename == file_content.filename:
                continue
            for word in words:
                if len(word) > 2 and word in pr_file.filename:
                    related_files.append(pr_file.filename)
                    break
    
    return list(set(related_files))

def get_function_at_line(content: str, line: int, language: str) -> Optional[Dict]:
    functions = extract_functions(content, language)
    if not functions:
        return None
        
    closest_func = None
    for func in functions:
        if func["line"] <= line:
            if closest_func is None or func["line"] > closest_func["line"]:
                closest_func = func
    
    return closest_func

def get_file_summary(content: str, language: str) -> str:
    lines = content.splitlines()
    num_lines = len(lines)
    num_functions = len(extract_functions(content, language))
    num_classes = len(extract_classes(content, language))
    imports = extract_imports(content, language)
    num_imports = len(imports)
    
    return f"File summary: {num_lines} lines, {num_classes} classes, {num_functions} functions, {num_imports} imports."
