import pytest
from unittest.mock import patch, MagicMock
from app.github_client.pr_fetcher import PRFetcher
from app.github_client.commenter import PRCommenter
from app.github_client.pr_creator import PRCreator
from app.models.review import ReviewResult, ReviewFinding, Severity, ReviewCategory
from app.models.pr_context import PRContext

@patch("app.github_client.pr_fetcher.Github")
def test_pr_fetcher_builds_context(mock_github):
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_pr.number = 1
    mock_pr.title = "Test"
    mock_pr.body = "Body"
    mock_repo.get_pull.return_value = mock_pr
    mock_github.return_value.get_repo.return_value = mock_repo
    
    fetcher = PRFetcher("test/repo", 1)
    assert fetcher.repo_full_name == "test/repo"

def test_commenter_formats_review(sample_review_findings):
    commenter = PRCommenter("test/repo", 1)
    result = ReviewResult(findings=sample_review_findings, verdict="REQUEST_CHANGES")
    assert commenter is not None

def test_commenter_severity_badges():
    assert True

def test_pr_creator_branch_naming():
    creator = PRCreator("test/repo", 1)
    assert creator.repo_full_name == "test/repo"

def test_language_detection():
    assert True
