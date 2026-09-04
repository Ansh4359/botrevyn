from enum import Enum
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    SUGGESTION = "SUGGESTION"
    INFO = "INFO"

class ReviewCategory(str, Enum):
    CODE_QUALITY = "CODE_QUALITY"
    SECURITY = "SECURITY"
    TEST_COVERAGE = "TEST_COVERAGE"
    STYLE = "STYLE"
    DOCUMENTATION = "DOCUMENTATION"
    PERFORMANCE = "PERFORMANCE"

class ReviewFinding(BaseModel):
    severity: Severity = Severity.INFO
    category: ReviewCategory = ReviewCategory.CODE_QUALITY
    file_path: str = "unknown"
    start_line: int = 1
    end_line: int = 1
    title: str = "Code Issue"
    description: str = ""
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None
    auto_fixable: bool = False

class FixSuggestion(BaseModel):
    file_path: str
    original_code: str
    fixed_code: str
    description: str
    finding_id: Optional[str] = None

class ReviewResult(BaseModel):
    pr_number: int
    repo_full_name: str
    findings: List[ReviewFinding]
    summary: str
    overall_verdict: str
    fix_suggestions: List[FixSuggestion] = []
    reviewed_at: datetime
    review_duration_seconds: float
