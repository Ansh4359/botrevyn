import re
from typing import Dict, List, Optional

LANGUAGE_PATTERNS = {
    "python": {
        "function": r"^\s*(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
        "class": r"^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\(|:)",
        "import": r"^\s*(?:import\s+|from\s+[a-zA-Z0-9_.]+\s+import\s+)",
    },
    "javascript": {
        "function": r"^\s*(?:async\s+)?(?:function\s+([a-zA-Z_][a-zA-Z0-9_]*)|(?:const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_][a-zA-Z0-9_]*)\s*=>|([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{)",
        "class": r"^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        "import": r"^\s*(?:import\s+.*from\s+['\"].*['\"]|const\s+.*=\s+require\(['\"].*['\"]\))",
    },
    "go": {
        "function": r"^\s*func\s+(?:\(\s*[a-zA-Z0-9_]+\s+\*?[a-zA-Z0-9_]+\s*\)\s+)?([a-zA-Z_][a-zA-Z0-9_]*)",
        "class": r"^\s*type\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+struct",
        "import": r"^\s*import\s+(?:\(|[\"'].*[\"'])",
    },
    "java": {
        "function": r"^\s*(?:public|protected|private|static|final|native|synchronized|abstract|transient|\s)*[\w<>,\[\]]+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
        "class": r"^\s*(?:public|protected|private|static|final|abstract|\s)*(?:class|interface|enum)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        "import": r"^\s*import\s+[a-zA-Z0-9_.]+;",
    }
}

def analyze_complexity(code: str, language: str) -> Dict:
    complexity = 1
    patterns = [
        r"\bif\b", r"\belse\b", r"\bfor\b", r"\bwhile\b", r"\bcase\b", 
        r"\bcatch\b", r"\bexcept\b", r"&&", r"\|\|", r"\band\b", r"\bor\b"
    ]
    for pattern in patterns:
        complexity += len(re.findall(pattern, code))
    
    return {
        "cyclomatic_complexity": complexity,
        "is_complex": complexity > 10
    }

def extract_functions(code: str, language: str) -> List[Dict]:
    functions = []
    lang_pats = LANGUAGE_PATTERNS.get(language, LANGUAGE_PATTERNS["python"])
    func_pattern = lang_pats.get("function")
    if not func_pattern:
        return functions
    
    lines = code.splitlines()
    for i, line in enumerate(lines):
        match = re.search(func_pattern, line)
        if match:
            name = next((g for g in match.groups() if g), "anonymous")
            functions.append({
                "name": name,
                "line": i + 1,
                "signature": line.strip()
            })
    return functions

def extract_classes(code: str, language: str) -> List[Dict]:
    classes = []
    lang_pats = LANGUAGE_PATTERNS.get(language, LANGUAGE_PATTERNS["python"])
    class_pattern = lang_pats.get("class")
    if not class_pattern:
        return classes
    
    lines = code.splitlines()
    for i, line in enumerate(lines):
        match = re.search(class_pattern, line)
        if match:
            classes.append({
                "name": match.group(1),
                "line": i + 1
            })
    return classes

def extract_imports(code: str, language: str) -> List[str]:
    imports = []
    lang_pats = LANGUAGE_PATTERNS.get(language, LANGUAGE_PATTERNS["python"])
    import_pattern = lang_pats.get("import")
    if not import_pattern:
        return imports
    
    for line in code.splitlines():
        if re.search(import_pattern, line):
            imports.append(line.strip())
    return imports

def detect_language(filename: str) -> str:
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "javascript",
        ".tsx": "javascript",
        ".go": "go",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".c": "c",
        ".rs": "rust",
        ".swift": "swift",
        ".kt": "kotlin"
    }
    for ext, lang in ext_map.items():
        if filename.endswith(ext):
            return lang
    return "unknown"
