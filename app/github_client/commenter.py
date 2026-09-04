import logging
import re
from typing import Optional, List, Dict
from app.github_client.client import get_github_client
from app.models.review import ReviewResult, ReviewFinding, Severity, ReviewCategory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Visual constants
# ---------------------------------------------------------------------------

VERDICT_HEADER = {
    "APPROVE": ("✅", "Changes Approved", "All checks passed — this PR is ready to merge."),
    "COMMENT": ("💬", "Review Complete", "Minor suggestions found — no blocking issues."),
    "REQUEST_CHANGES": ("🚨", "Changes Requested", "Blocking issues were detected and must be resolved before merging."),
}

SEVERITY_ICON = {
    Severity.CRITICAL: "🔴",
    Severity.MAJOR: "🟠",
    Severity.MINOR: "🟡",
    Severity.SUGGESTION: "💡",
    Severity.INFO: "ℹ️",
}

SEVERITY_LABEL = {
    Severity.CRITICAL: "Critical",
    Severity.MAJOR: "Major",
    Severity.MINOR: "Minor",
    Severity.SUGGESTION: "Suggestion",
    Severity.INFO: "Info",
}

CATEGORY_ICON = {
    ReviewCategory.CODE_QUALITY: "🐛",
    ReviewCategory.SECURITY: "🔒",
    ReviewCategory.TEST_COVERAGE: "🧪",
    ReviewCategory.STYLE: "🎨",
    ReviewCategory.DOCUMENTATION: "📝",
    ReviewCategory.PERFORMANCE: "⚡",
}

CATEGORY_LABEL = {
    ReviewCategory.CODE_QUALITY: "Code Quality",
    ReviewCategory.SECURITY: "Security",
    ReviewCategory.TEST_COVERAGE: "Test Coverage",
    ReviewCategory.STYLE: "Style & Conventions",
    ReviewCategory.DOCUMENTATION: "Documentation",
    ReviewCategory.PERFORMANCE: "Performance",
}


class PRCommenter:
    """Posts structured review comments to GitHub PRs."""

    def __init__(self, installation_id: Optional[int] = None):
        self.github_client = get_github_client(installation_id)

    # ------------------------------------------------------------------
    # Diff position mapping
    # ------------------------------------------------------------------

    def _map_line_to_diff_position(self, patch_text: str, target_line: int) -> Optional[int]:
        """Map a file line number to a diff hunk position for inline review comments."""
        try:
            position = 0
            current_new_line = 0
            for raw_line in patch_text.splitlines():
                if raw_line.startswith("@@"):
                    # Parse hunk header: @@ -old,count +new,count @@
                    match = re.search(r"\+(\d+)", raw_line)
                    if match:
                        current_new_line = int(match.group(1)) - 1
                    position += 1
                    continue
                position += 1
                if raw_line.startswith("-"):
                    continue  # deleted line — doesn't advance new-file counter
                current_new_line += 1
                if current_new_line == target_line:
                    return position
            return None
        except Exception as e:
            logger.error(f"Error mapping line {target_line} to diff position: {e}")
            return None

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _severity_bar(counts: Dict[Severity, int]) -> str:
        """Render a compact inline severity bar: 🔴 3  🟠 5  🟡 2"""
        parts = []
        for sev in Severity:
            if sev in counts:
                parts.append(f"{SEVERITY_ICON[sev]} **{counts[sev]}** {SEVERITY_LABEL[sev]}")
        return " &nbsp;·&nbsp; ".join(parts)

    @staticmethod
    def _format_finding_row(f: ReviewFinding, repo_full_name: str, pr_number: int) -> str:
        """Format a single finding as a clean table-like bullet."""
        icon = SEVERITY_ICON.get(f.severity, "ℹ️")
        sev = SEVERITY_LABEL.get(f.severity, "Info")

        # Build a linked file reference
        file_link = f"[`{f.file_path}:{f.start_line}`](https://github.com/{repo_full_name}/pull/{pr_number}/files#diff-{f.file_path})"

        lines = [f"> {icon} **{sev}** &nbsp;|&nbsp; {file_link}"]
        lines.append(f"> **{f.title}**")
        lines.append(f"> {f.description}")

        if f.suggestion:
            lines.append(f">")
            lines.append(f"> 💡 **Suggestion:** {f.suggestion}")

        if f.code_snippet:
            # Indent code inside the blockquote
            snippet_lines = f.code_snippet.strip().splitlines()
            lines.append(f">")
            lines.append(f"> ```")
            for sl in snippet_lines[:8]:  # Cap snippet preview
                lines.append(f"> {sl}")
            if len(snippet_lines) > 8:
                lines.append(f"> // ... ({len(snippet_lines) - 8} more lines)")
            lines.append(f"> ```")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Main review body
    # ------------------------------------------------------------------

    def _format_review_body(self, result: ReviewResult) -> str:
        """Build a polished, SaaS-grade review comment."""
        verdict_info = VERDICT_HEADER.get(
            result.overall_verdict,
            ("📋", "Review Complete", ""),
        )
        icon, title, subtitle = verdict_info

        # ── Header ──
        body = f"## {icon} BotRevyn — {title}\n\n"
        body += f"_{subtitle}_\n\n"

        # ── Quality Gate summary ──
        severity_counts: Dict[Severity, int] = {}
        for f in result.findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

        total = len(result.findings)
        body += "<table>\n<tr>\n"
        body += f'<td><strong>Total Issues</strong></td><td><code>{total}</code></td>\n'
        body += "</tr>\n<tr>\n"
        body += f'<td><strong>Breakdown</strong></td><td>{self._severity_bar(severity_counts)}</td>\n'
        body += "</tr>\n<tr>\n"
        body += f'<td><strong>Verdict</strong></td><td><code>{result.overall_verdict}</code></td>\n'
        body += "</tr>\n</table>\n\n"

        # ── Per-file summary table ──
        files_seen: Dict[str, List[ReviewFinding]] = {}
        for f in result.findings:
            files_seen.setdefault(f.file_path, []).append(f)

        body += "<details>\n<summary>📂 <strong>Files reviewed</strong></summary>\n\n"
        body += "| File | Issues | Highest Severity |\n"
        body += "|:-----|:------:|:-----------------|\n"
        for fpath, findings in files_seen.items():
            count = len(findings)
            worst = min(findings, key=lambda x: list(Severity).index(x.severity))
            worst_badge = f"{SEVERITY_ICON[worst.severity]} {SEVERITY_LABEL[worst.severity]}"
            body += f"| `{fpath}` | {count} | {worst_badge} |\n"
        body += "\n</details>\n\n"

        # ── Findings grouped by category ──
        body += "---\n\n"
        body += "### 📋 Detailed Findings\n\n"

        categories_seen: Dict[ReviewCategory, List[ReviewFinding]] = {}
        for f in result.findings:
            categories_seen.setdefault(f.category, []).append(f)

        # Sort categories: ones with critical/major first
        def _category_priority(cat: ReviewCategory) -> int:
            findings = categories_seen[cat]
            if any(f.severity == Severity.CRITICAL for f in findings):
                return 0
            if any(f.severity == Severity.MAJOR for f in findings):
                return 1
            return 2

        for category in sorted(categories_seen.keys(), key=_category_priority):
            findings = categories_seen[category]
            cat_icon = CATEGORY_ICON.get(category, "📋")
            cat_label = CATEGORY_LABEL.get(category, category.value)
            sev_counts_cat: Dict[Severity, int] = {}
            for f in findings:
                sev_counts_cat[f.severity] = sev_counts_cat.get(f.severity, 0) + 1

            cat_summary = " &nbsp; ".join(
                f"{SEVERITY_ICON[s]}&thinsp;{c}"
                for s, c in sev_counts_cat.items()
            )

            body += f"<details>\n"
            body += f"<summary>{cat_icon} <strong>{cat_label}</strong> — {len(findings)} issue(s) &nbsp; {cat_summary}</summary>\n\n"

            for f in findings:
                body += self._format_finding_row(f, result.repo_full_name, result.pr_number) + "\n\n"

            body += "</details>\n\n"

        # ── Auto-fix section ──
        if result.fix_suggestions:
            body += "---\n\n"
            body += f"### 🔧 Auto-Fix Available\n\n"
            body += f"**{len(result.fix_suggestions)}** issue(s) can be automatically fixed. "
            body += "A fix PR will be created shortly.\n\n"

        # ── Footer ──
        body += "---\n\n"
        duration = result.review_duration_seconds
        if duration >= 60:
            time_str = f"{duration / 60:.1f}m"
        else:
            time_str = f"{duration:.1f}s"

        body += f"<sub>🤖 Powered by <strong>BotRevyn</strong> &nbsp;·&nbsp; "
        body += f"Reviewed in {time_str} &nbsp;·&nbsp; "
        body += f"{total} finding(s) across {len(files_seen)} file(s)</sub>\n"

        return body

    def _format_approve_body(self, result: ReviewResult) -> str:
        """Format a clean approval message when no issues are found."""
        body = "## ✅ BotRevyn — All Clear\n\n"
        body += "No issues were found in the changed files. This PR is ready to merge.\n\n"

        # Show what was checked
        body += "<details>\n<summary>🔍 <strong>What was checked</strong></summary>\n\n"
        body += "| Category | Status |\n"
        body += "|:---------|:------:|\n"
        for cat in ReviewCategory:
            cat_icon = CATEGORY_ICON.get(cat, "📋")
            cat_label = CATEGORY_LABEL.get(cat, cat.value)
            body += f"| {cat_icon} {cat_label} | ✅ Passed |\n"
        body += "\n</details>\n\n"

        body += "---\n\n"
        duration = result.review_duration_seconds
        time_str = f"{duration:.1f}s" if duration < 60 else f"{duration / 60:.1f}m"
        body += f"<sub>🤖 Powered by <strong>BotRevyn</strong> &nbsp;·&nbsp; "
        body += f"Reviewed in {time_str}</sub>\n"

        return body

    # ------------------------------------------------------------------
    # Inline finding comment (for per-line review comments)
    # ------------------------------------------------------------------

    @staticmethod
    def _format_inline_comment(finding: ReviewFinding) -> str:
        """Format a single finding for an inline review comment on a specific line."""
        icon = SEVERITY_ICON.get(finding.severity, "ℹ️")
        sev = SEVERITY_LABEL.get(finding.severity, "Info")

        lines = [f"**{icon} {sev} — {finding.title}**"]
        lines.append("")
        lines.append(finding.description)

        if finding.suggestion:
            lines.append("")
            lines.append(f"💡 **Suggestion:** {finding.suggestion}")

        if finding.code_snippet:
            lines.append("")
            lines.append("```")
            lines.append(finding.code_snippet.strip())
            lines.append("```")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def post_review(self, repo_full_name: str, pr_number: int, result: ReviewResult) -> None:
        """Post a full review to the GitHub PR."""
        pr = self.github_client.get_pull_request(repo_full_name, pr_number)

        if not result.findings:
            body = self._format_approve_body(result)
            pr.create_review(body=body, event="COMMENT")
            return

        body = self._format_review_body(result)

        # Build inline comments where we can map to diff positions
        inline_comments: List[dict] = []
        pr_files = {f.filename: f for f in pr.get_files()}

        for finding in result.findings:
            diff_file = pr_files.get(finding.file_path)
            if diff_file and diff_file.patch:
                position = self._map_line_to_diff_position(
                    diff_file.patch, finding.start_line
                )
                if position:
                    inline_comments.append({
                        "body": self._format_inline_comment(finding),
                        "path": finding.file_path,
                        "position": position,
                    })

        pr.create_review(body=body, event="COMMENT", comments=inline_comments)

    def post_error_comment(self, repo_full_name: str, pr_number: int, message: str) -> None:
        """Post an error comment when the review pipeline fails."""
        pr = self.github_client.get_pull_request(repo_full_name, pr_number)

        body = "## ⚠️ BotRevyn — Review Failed\n\n"
        body += "An error occurred during the automated code review.\n\n"
        body += f"```\n{message}\n```\n\n"
        body += "---\n\n"
        body += "<sub>🤖 Powered by <strong>BotRevyn</strong> &nbsp;·&nbsp; "
        body += "The review will be retried automatically.</sub>\n"

        pr.create_issue_comment(body)
