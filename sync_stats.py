from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


VALID_DIFFICULTIES = {"easy", "medium", "hard"}
README_TOPICS_START = "<!---LeetCode Topics Start-->"
README_TOPICS_END = "<!---LeetCode Topics End-->"
TOPIC_ROW_RE = re.compile(r"^\| \[(?P<label>[^\]]+)\]\((?P<url>[^)]+)\) \|$")
GITHUB_TREE_URL = "https://github.com/rohini8307-dev/LEETCODE/tree/master"
SOLUTION_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".cxx",
    ".go",
    ".java",
    ".js",
    ".kt",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".sql",
    ".swift",
    ".ts",
}
PROBLEM_FILE_RE = re.compile(r"^\d{4}-.+")  # Match files like "0821-shortest-distance"


class StatsError(Exception):
    pass


def relative_to_repo(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def git_hash_object(repo_root: Path, path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", relative_to_repo(repo_root, path)],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise StatsError(f"git hash-object failed for {path}: {message}")
    return result.stdout.strip()


def load_stats(stats_path: Path) -> dict[str, Any]:
    try:
        with stats_path.open("r", encoding="utf-8") as handle:
            stats = json.load(handle)
    except FileNotFoundError as exc:
        raise StatsError("stats.json was not found") from exc
    except json.JSONDecodeError as exc:
        raise StatsError(f"stats.json is not valid JSON: {exc}") from exc

    leetcode = stats.get("leetcode")
    if not isinstance(leetcode, dict):
        raise StatsError('stats.json must contain an object at key "leetcode"')
    shas = leetcode.get("shas")
    if not isinstance(shas, dict):
        raise StatsError('stats.json must contain an object at key "leetcode.shas"')
    return stats


def write_stats(stats_path: Path, stats: dict[str, Any]) -> None:
    with stats_path.open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=4)
        handle.write("\n")


def topic_folders(repo_root: Path) -> dict[str, list[Path]]:
    """
    Scan repo for topic folders containing solution files.
    Returns a dict: {topic_name: [solution_file_paths]}
    """
    topics: dict[str, list[Path]] = {}
    
    for item in sorted(repo_root.iterdir()):
        if not item.is_dir():
            continue
        
        # Skip special folders
        if item.name.startswith('.') or item.name in {'automation', 'extension'}:
            continue
        
        # Find solution files in this folder
        solution_files = [
            f for f in item.iterdir()
            if f.is_file() and f.suffix.lower() in SOLUTION_EXTENSIONS 
            and PROBLEM_FILE_RE.match(f.stem)
        ]
        
        if solution_files:
            topics[item.name] = sorted(solution_files, key=lambda f: f.name)
    
    return topics


def problem_sort_key(solution_file_name: str) -> tuple[int, str]:
    """Extract numeric ID from solution file for sorting."""
    stem = Path(solution_file_name).stem
    match = re.match(r"^(\d+)", stem)
    if match:
        return int(match.group(1)), stem
    return sys.maxsize, stem


def solution_file_display_name(solution_file_path: Path) -> str:
    """Get display name for solution file (without extension)."""
    return solution_file_path.stem


def entry_matches(entry: Any, expected: dict[str, str]) -> bool:
    return isinstance(entry, dict) and entry == expected


def set_if_changed(
    container: dict[str, Any],
    key: str,
    value: Any,
    label: str,
    changes: list[str],
) -> None:
    if container.get(key) != value:
        changes.append(label)
        container[key] = value


def problem_topic_row(topic: str, solution_filename_with_ext: str) -> str:
    """Generate a table row for a problem in the README with proper link to the .py file."""
    display_name = Path(solution_filename_with_ext).stem
    url = f"{GITHUB_TREE_URL}/{topic}/{solution_filename_with_ext}"
    return f"| [{display_name}]({url}) |"


def problem_info_from_topic_row(match: re.Match[str]) -> tuple[str, str]:
    """Extract problem file display name and topic from a README topic row.
    Returns (problem_file_display_without_ext, topic_from_url)
    """
    label = match.group("label")
    url = match.group("url")
    github_tree_prefix = f"{GITHUB_TREE_URL}/"
    
    if url.startswith(github_tree_prefix):
        path_part = url[len(github_tree_prefix):]
        parts = path_part.split('/')
        if len(parts) == 2:
            topic, filename_with_ext = parts
            # Extract display name (without extension)
            display_name = Path(filename_with_ext).stem
            return display_name, topic
    
    return label, ""


def split_topic_sections(
    block: list[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    intro: list[str] = []
    sections: list[dict[str, Any]] = []
    index = 0

    while index < len(block) and not block[index].startswith("## "):
        intro.append(block[index])
        index += 1

    while index < len(block):
        heading = block[index]
        if not heading.startswith("## "):
            raise StatsError(f"unexpected line in README topics block: {heading}")

        topic = heading[3:].strip()
        if not topic:
            raise StatsError("README topic heading cannot be empty")

        index += 1
        table_lines: list[str] = []
        while index < len(block) and not block[index].startswith("## "):
            table_lines.append(block[index])
            index += 1

        non_empty_lines = [line for line in table_lines if line.strip()]
        if len(non_empty_lines) < 2:
            raise StatsError(f"{topic}: topic table is missing its header")
        if non_empty_lines[0] != "|  |" or non_empty_lines[1] != "| ------- |":
            raise StatsError(f"{topic}: topic table header is not in the expected format")

        rows: list[tuple[str, str, str]] = []  # (problem_file_display, topic_name, row_html)
        for row in non_empty_lines[2:]:
            match = TOPIC_ROW_RE.match(row)
            if not match:
                raise StatsError(f"{topic}: invalid topic row: {row}")
            problem_file, url_topic = problem_info_from_topic_row(match)
            rows.append((problem_file, url_topic, row))

        sections.append({"topic": topic, "rows": rows})

    return intro, sections


def render_topic_sections(
    intro: list[str],
    sections: list[dict[str, Any]],
) -> list[str]:
    lines = intro[:]
    for section in sections:
        # Sort rows by problem file (numeric ID first)
        sorted_rows = sorted(
            section["rows"], 
            key=lambda row: problem_sort_key(row[0])
        )
        lines.extend([f"## {section['topic']}", "|  |", "| ------- |"])
        lines.extend(row_html for _, _, row_html in sorted_rows)
    return lines


def regenerate_readme_from_folders(repo_root: Path) -> tuple[list[str], list[str]]:
    """
    Regenerate README topics section completely from actual topic folders on disk.
    Returns (new_lines, changes)
    """
    readme_path = repo_root / "README.md"
    if not readme_path.is_file():
        raise StatsError("README.md was not found")
    
    original_text = readme_path.read_text(encoding="utf-8")
    lines = original_text.splitlines()
    
    start_indexes = [i for i, line in enumerate(lines) if line == README_TOPICS_START]
    end_indexes = [i for i, line in enumerate(lines) if line == README_TOPICS_END]
    if len(start_indexes) != 1 or len(end_indexes) != 1:
        raise StatsError("README.md must have exactly one LeetCode topics start marker and one end marker")
    
    start_index = start_indexes[0]
    end_index = end_indexes[0]
    if start_index >= end_index:
        raise StatsError("README.md LeetCode topics markers are out of order")
    
    intro, old_sections = split_topic_sections(lines[start_index + 1 : end_index])
    changes: list[str] = []
    
    # Scan actual folders for solutions
    topics_dict = topic_folders(repo_root)
    new_sections = []
    
    for topic_name in sorted(topics_dict.keys()):
        solution_files = topics_dict[topic_name]
        rows = []
        for solution_file in sorted(solution_files, key=lambda f: problem_sort_key(f.name)):
            display_name = solution_file.stem
            row_html = problem_topic_row(topic_name, solution_file.name)
            rows.append((display_name, topic_name, row_html))
        
        if rows:
            new_sections.append({"topic": topic_name, "rows": rows})
            changes.append(f"README.md: regenerate topic {topic_name}")
    
    new_lines = (
        lines[: start_index + 1]
        + render_topic_sections(intro, new_sections)
        + lines[end_index:]
    )
    new_text = "\n".join(new_lines) + "\n"
    
    if new_text != original_text:
        readme_path.write_text(new_text, encoding="utf-8")
    
    return new_lines, changes


def update_root_readme_topics(
    repo_root: Path,
    topic_name: str,
    solution_filename_with_ext: str,
) -> list[str]:
    """
    Update README.md to add a solution file to a topic section.
    
    Args:
        repo_root: Repository root path
        topic_name: Name of the topic folder (e.g., "Array", "Sliding Window")
        solution_filename_with_ext: Solution file name WITH extension (e.g., "0821-shortest-distance.py")
    """
    # Extract display name without extension for internal tracking
    solution_file_display = Path(solution_filename_with_ext).stem
    
    readme_path = repo_root / "README.md"
    if not readme_path.is_file():
        raise StatsError("README.md was not found")

    topic_dir = repo_root / topic_name
    if not topic_dir.is_dir():
        raise StatsError(f"topic folder not found: {topic_name}")

    original_text = readme_path.read_text(encoding="utf-8")
    lines = original_text.splitlines()

    start_indexes = [i for i, line in enumerate(lines) if line == README_TOPICS_START]
    end_indexes = [i for i, line in enumerate(lines) if line == README_TOPICS_END]
    if len(start_indexes) != 1 or len(end_indexes) != 1:
        raise StatsError("README.md must have exactly one LeetCode topics start marker and one end marker")

    start_index = start_indexes[0]
    end_index = end_indexes[0]
    if start_index >= end_index:
        raise StatsError("README.md LeetCode topics markers are out of order")

    intro, sections = split_topic_sections(lines[start_index + 1 : end_index])
    topic_names = [section["topic"] for section in sections]
    duplicate_topics = sorted(
        topic for topic in set(topic_names) if topic_names.count(topic) > 1
    )
    if duplicate_topics:
        raise StatsError(f"README.md has duplicate topic sections: {', '.join(duplicate_topics)}")

    target_row = problem_topic_row(topic_name, solution_filename_with_ext)
    changes: list[str] = []

    # Update existing sections
    for section in sections:
        section_topic = section["topic"]
        old_rows = section["rows"]
        
        # Remove old entry for this problem if it exists (with any topic in URL)
        rows_without_problem = [
            (prob_file, url_topic, row_html)
            for prob_file, url_topic, row_html in old_rows
            if prob_file != solution_file_display
        ]

        if section_topic == topic_name:
            # Add to this topic
            section["rows"] = rows_without_problem + [(solution_file_display, topic_name, target_row)]
            if len(rows_without_problem) == len(old_rows):
                # Problem wasn't already in this topic
                changes.append(f"README.md: add {solution_file_display} to {topic_name}")
            else:
                # Problem was updated
                changes.append(f"README.md: update {solution_file_display} in {topic_name}")
        else:
            # Remove from other topics
            if len(rows_without_problem) < len(old_rows):
                changes.append(f"README.md: remove {solution_file_display} from {section_topic}")
            section["rows"] = rows_without_problem

    # Create topic section if it doesn't exist
    existing_topics = {section["topic"] for section in sections}
    if topic_name not in existing_topics:
        sections.append({"topic": topic_name, "rows": [(solution_file_display, topic_name, target_row)]})
        existing_topics.add(topic_name)
        changes.append(f"README.md: create topic {topic_name} with {solution_file_display}")

    # Remove empty topic sections
    non_empty_sections: list[dict[str, Any]] = []
    for section in sections:
        if section["rows"]:
            non_empty_sections.append(section)
        else:
            changes.append(f"README.md: remove empty topic {section['topic']}")

    new_lines = (
        lines[: start_index + 1]
        + render_topic_sections(intro, non_empty_sections)
        + lines[end_index:]
    )
    new_text = "\n".join(new_lines) + "\n"

    if new_text != original_text:
        if not changes:
            changes.append("README.md: sort topic rows")
        readme_path.write_text(new_text, encoding="utf-8")

    return changes


def build_expected_stats(
    repo_root: Path,
    stats: dict[str, Any],
    *,
    prompt_for_difficulty: bool,
    topic_override: str | None = None,
    difficulty_override: str | None = None,
    solution_file_override: str | None = None,
    extension_override: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    expected = copy.deepcopy(stats)
    leetcode = expected["leetcode"]
    shas = leetcode["shas"]
    changes: list[str] = []
    counts: Counter[str] = Counter()
    seen_entries: set[str] = set()

    # Scan for solution files in topic folders
    topics_dict = topic_folders(repo_root)
    
    for topic_name, solution_files in sorted(topics_dict.items()):
        for solution_file in solution_files:
            problem_file_display = solution_file_display_name(solution_file)
            entry_key = f"{topic_name}/{problem_file_display}"
            seen_entries.add(entry_key)
            
            # Get or create entry
            old_entry = shas.get(entry_key)
            entry = old_entry if isinstance(old_entry, dict) else {}
            
            # Determine difficulty
            if difficulty_override and solution_file_override == problem_file_display:
                difficulty = difficulty_override
            else:
                difficulty = entry.get("difficulty", "").strip().lower()
                if difficulty not in VALID_DIFFICULTIES:
                    if prompt_for_difficulty:
                        while True:
                            try:
                                value = input(f"Difficulty for {topic_name}/{problem_file_display} (easy/medium/hard): ")
                            except EOFError as exc:
                                raise StatsError(
                                    f"{entry_key}: difficulty is required, but input was not available"
                                ) from exc
                            difficulty = value.strip().lower()
                            if difficulty in VALID_DIFFICULTIES:
                                break
                            print("Please enter easy, medium, or hard.")
                        changes.append(f"{entry_key}: set difficulty to {difficulty}")
                    else:
                        changes.append(
                            f"{entry_key}: missing or invalid difficulty; run --write and enter one"
                        )
                        continue

            counts[difficulty] += 1
            
            # Calculate expected entry
            solution_hash = git_hash_object(repo_root, solution_file)
            expected_entry = {
                solution_file.name: solution_hash,
                "difficulty": difficulty,
            }

            # Check if entry needs updating
            if not entry_matches(entry, expected_entry):
                if old_entry is None:
                    changes.append(f"{entry_key}: add stats entry")
                else:
                    old_solution_keys = [
                        key for key in entry
                        if key not in {"difficulty"}
                    ]
                    if old_solution_keys != [solution_file.name]:
                        changes.append(f"{entry_key}: use solution key {solution_file.name}")
                    elif entry.get(solution_file.name) != solution_hash:
                        changes.append(f"{entry_key}: update solution hash")
                    
                    if entry.get("difficulty") != difficulty:
                        changes.append(f"{entry_key}: update difficulty")

                shas[entry_key] = expected_entry

    # Remove stale entries
    stale_keys = sorted(
        key for key in shas
        if "/" in key and key not in seen_entries
    )
    for key in stale_keys:
        changes.append(f"{key}: remove stale stats entry")
        del shas[key]

    # Update root README hash
    root_readme = repo_root / "README.md"
    if root_readme.is_file():
        root_readme_entry = shas.get("README.md")
        if not isinstance(root_readme_entry, dict):
            root_readme_entry = {}
            shas["README.md"] = root_readme_entry
        root_hash = git_hash_object(repo_root, root_readme)
        if root_readme_entry.get("") != root_hash:
            changes.append("README.md: update root hash")
            root_readme_entry[""] = root_hash

    # Update difficulty counts
    set_if_changed(leetcode, "easy", counts["easy"], "easy: update count", changes)
    set_if_changed(leetcode, "medium", counts["medium"], "medium: update count", changes)
    set_if_changed(leetcode, "hard", counts["hard"], "hard: update count", changes)
    set_if_changed(
        leetcode,
        "solved",
        sum(counts.values()),
        "solved: update count",
        changes,
    )

    return expected, changes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check or update LeetCode stats.json hashes, counts, and root README topics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python sync_stats.py --check\n"
            "  python sync_stats.py --write\n"
            "  python sync_stats.py --write --topic Array --problem-file 0189-rotate-array "
            "--difficulty medium --extension .py"
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="report required stats.json changes without editing",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="update stats.json in place; prompts for missing difficulty values unless --difficulty is provided",
    )
    parser.add_argument(
        "--topic",
        help="topic folder name for a newly added solution file",
    )
    parser.add_argument(
        "--problem-file",
        help="problem file name (without extension) for the solution file being added",
    )
    parser.add_argument(
        "--difficulty",
        choices=sorted(VALID_DIFFICULTIES),
        help="difficulty to store for the solution",
    )
    parser.add_argument(
        "--extension",
        help="file extension of the solution file (e.g., .py, .js)",
    )

    args = parser.parse_args()
    topic_args = [args.topic is not None, args.problem_file is not None, args.difficulty is not None, args.extension is not None]
    if any(topic_args):
        if not args.write:
            parser.error("--topic, --problem_file, --difficulty, and --extension can only be used with --write")
        if not all(topic_args):
            parser.error("--topic, --problem_file, --difficulty, and --extension must be used together")
    return args


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent
    stats_path = repo_root / "stats.json"

    try:
        readme_changes: list[str] = []
        topic_override = None
        difficulty_override = None
        solution_file_override = None
        extension_override = None
        
        if args.topic:
            # Update README with the new solution (pass full filename with extension)
            full_solution_filename = f"{args.problem_file}{args.extension}"
            readme_changes = update_root_readme_topics(
                repo_root,
                args.topic,
                full_solution_filename,
            )
            topic_override = args.topic
            difficulty_override = args.difficulty
            solution_file_override = args.problem_file
            extension_override = args.extension
        elif args.write:
            # When just running --write without --topic, regenerate entire README from folders
            _, readme_changes = regenerate_readme_from_folders(repo_root)

        current = load_stats(stats_path)
        expected, changes = build_expected_stats(
            repo_root,
            current,
            prompt_for_difficulty=args.write,
            topic_override=topic_override,
            difficulty_override=difficulty_override,
            solution_file_override=solution_file_override,
            extension_override=extension_override,
        )
        changes = readme_changes + changes
    except StatsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.check:
        if changes:
            print("stats.json needs updates:")
            for change in changes:
                print(f"- {change}")
            return 1
        print("stats.json is up to date.")
        return 0

    if changes:
        write_stats(stats_path, expected)
        target = "README.md and stats.json" if readme_changes else "stats.json"
        print(f"Updated {target} ({len(changes)} change(s)):")
        for change in changes:
            print(f"- {change}")
    else:
        print("stats.json is already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())