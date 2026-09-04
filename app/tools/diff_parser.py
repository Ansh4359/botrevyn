import io
from typing import Optional, List, Dict, Tuple
from unidiff import PatchSet
from app.models.pr_context import FileDiff

def parse_unified_diff(diff_text: str) -> List[FileDiff]:
    try:
        patch_set = PatchSet(io.StringIO(diff_text))
    except Exception:
        return []
        
    file_diffs = []
    for patched_file in patch_set:
        file_diffs.append(FileDiff(
            filename=patched_file.path,
            status="added" if patched_file.is_added_file else "removed" if patched_file.is_removed_file else "modified",
            patch=str(patched_file),
            additions=patched_file.added,
            deletions=patched_file.removed
        ))
    return file_diffs

def get_added_lines(patch: str) -> List[Tuple[int, str]]:
    added_lines = []
    try:
        patch_set = PatchSet(io.StringIO(patch))
        for patched_file in patch_set:
            for hunk in patched_file:
                for line in hunk:
                    if line.is_added:
                        added_lines.append((line.target_line_no, line.value.rstrip('\n')))
    except Exception:
        pass
    return added_lines

def get_modified_hunks(patch: str) -> List[Dict]:
    hunks = []
    try:
        patch_set = PatchSet(io.StringIO(patch))
        for patched_file in patch_set:
            for hunk in patched_file:
                start_line = hunk.target_start
                end_line = hunk.target_start + hunk.target_length - 1
                content = str(hunk)
                hunks.append({
                    "start_line": start_line,
                    "end_line": end_line,
                    "content": content
                })
    except Exception:
        pass
    return hunks

def map_line_to_diff_position(patch: str, target_line: int) -> Optional[int]:
    try:
        patch_set = PatchSet(io.StringIO(patch))
        position = 1
        for patched_file in patch_set:
            for hunk in patched_file:
                for line in hunk:
                    if line.target_line_no == target_line and line.is_added:
                        return position
                    position += 1
    except Exception:
        pass
    return None

def extract_context_around_line(content: str, line: int, context_lines: int = 5) -> str:
    lines = content.splitlines()
    start_idx = max(0, line - 1 - context_lines)
    end_idx = min(len(lines), line + context_lines)
    return "\n".join(lines[start_idx:end_idx])
