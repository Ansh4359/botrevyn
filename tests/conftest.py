import pytest
from app.models.webhook_payload import WebhookPayload, PullRequest, Repository
from app.models.pr_context import PRContext, FileDiff, FileContent
from app.models.review import ReviewResult, ReviewFinding, Severity, ReviewCategory, FixSuggestion
from app.config import Settings

@pytest.fixture
def settings_override():
    return Settings(
        github_token="mock_token",
        webhook_secret="mock_secret",
        redis_url="redis://localhost:6379/0",
        llm_model="gemini-1.5-pro",
        google_api_key="mock_google_key",
        auto_fix_enabled=True,
    )

@pytest.fixture
def sample_webhook_payload():
    return {
        "action": "opened",
        "pull_request": {
            "number": 1,
            "title": "Test PR",
            "body": "Test body",
            "base": {"ref": "main"},
            "head": {"ref": "feature-branch"}
        },
        "repository": {
            "full_name": "test/repo"
        }
    }

@pytest.fixture
def sample_file_content():
    return FileContent(
        filename="main.py",
        content="def add(a, b):\n    return a - b\n"
    )

@pytest.fixture
def sample_diff():
    return "--- a/main.py\n+++ b/main.py\n@@ -1,2 +1,2 @@\n-def add(a, b):\n-    return a + b\n+def add(a, b):\n+    return a - b\n"

@pytest.fixture
def sample_pr_context(sample_file_content, sample_diff):
    return PRContext(
        repo_full_name="test/repo",
        pr_number=1,
        title="Test PR",
        description="Test body",
        changed_files=["main.py"],
        file_diffs=[FileDiff(filename="main.py", patch=sample_diff, status="modified")],
        file_contents=[sample_file_content]
    )

@pytest.fixture
def sample_review_findings():
    return [
        ReviewFinding(
            filename="main.py",
            line_number=2,
            message="Subtraction used in an add function.",
            severity=Severity.CRITICAL,
            category=ReviewCategory.BUG,
            fix_suggestion=FixSuggestion(
                target_content="    return a - b\n",
                replacement_content="    return a + b\n"
            )
        )
    ]
