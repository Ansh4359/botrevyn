import json
import subprocess
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class LintResult:
    line: int
    column: int
    code: str
    message: str
    severity: str

def run_linter(code: str, filename: str, language: str) -> List[Dict]:
    if language == "python":
        results = _run_ruff(code, filename)
        return [
            {
                "line": r.line,
                "column": r.column,
                "code": r.code,
                "message": r.message,
                "severity": r.severity
            } for r in results
        ]
    else:
        return [{"message": f"Linting for {language} is not yet implemented.", "line": 0, "column": 0, "code": "", "severity": "info"}]

def _run_ruff(code: str, filename: str) -> List[LintResult]:
    results = []
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", "--stdin-filename", filename, "-"],
            input=code.encode('utf-8'),
            capture_output=True,
            check=False
        )
        if result.stdout:
            data = json.loads(result.stdout)
            for issue in data:
                results.append(LintResult(
                    line=issue.get("location", {}).get("row", 0),
                    column=issue.get("location", {}).get("column", 0),
                    code=issue.get("code", "UNKNOWN"),
                    message=issue.get("message", ""),
                    severity="error"
                ))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    except Exception:
        pass
    return results
