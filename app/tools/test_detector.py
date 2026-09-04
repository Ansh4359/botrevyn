import os
import re
from typing import List, Dict
from app.models.pr_context import FileContent
from app.tools.code_analyzer import extract_functions, detect_language

def detect_test_files(files: List[str]) -> List[str]:
    test_files = []
    patterns = [r"^test_.*", r".*_test\..*", r".*_spec\..*", r".*\.test\..*", r".*\.spec\..*"]
    for f in files:
        basename = os.path.basename(f)
        for pattern in patterns:
            if re.match(pattern, basename):
                test_files.append(f)
                break
    return test_files

def find_untested_functions(source_files: List[FileContent], test_files: List[FileContent]) -> List[Dict]:
    test_content_combined = "\n".join([f.content for f in test_files])
    
    untested = []
    for src_file in source_files:
        lang = detect_language(src_file.filename)
        functions = extract_functions(src_file.content, lang)
        
        for func in functions:
            name = func["name"]
            if name not in test_content_combined:
                untested.append({
                    "file": src_file.filename,
                    "function": name,
                    "line": func["line"]
                })
    return untested

def suggest_test_file_path(source_path: str) -> str:
    dir_name = os.path.dirname(source_path)
    base_name = os.path.basename(source_path)
    
    if "src/" in source_path:
        test_dir = dir_name.replace("src/", "tests/")
    else:
        test_dir = os.path.join(dir_name, "tests")
        
    name, ext = os.path.splitext(base_name)
    if ext == ".py":
        test_name = f"test_{name}{ext}"
    elif ext in [".js", ".ts"]:
        test_name = f"{name}.test{ext}"
    elif ext == ".go":
        test_name = f"{name}_test{ext}"
    else:
        test_name = f"test_{name}{ext}"
        
    return os.path.join(test_dir, test_name)

def generate_test_stub(function_name: str, file_path: str, language: str) -> str:
    if language == "python":
        return f"def test_{function_name}():\n    # TODO: Implement test for {function_name}\n    assert False\n"
    elif language == "javascript":
        return f"test('{function_name} works correctly', () => {{\n    // TODO: Implement test for {function_name}\n    expect(true).toBe(false);\n}});\n"
    elif language == "go":
        test_name = function_name[0].upper() + function_name[1:] if function_name else "Func"
        return f"func Test{test_name}(t *testing.T) {{\n    // TODO: Implement test for {function_name}\n    t.Fail()\n}}\n"
    else:
        return f"// TODO: Write test for {function_name}\n"
