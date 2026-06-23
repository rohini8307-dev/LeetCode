from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


HOST = "127.0.0.1"
DEFAULT_PORT = 8765
TOKEN_HEADER = "X-Local-LeetCode-Token"
TOKEN_FILE = "local_leetcode_token.json"
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
PROBLEM_FOLDER_RE = re.compile(r"^\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
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
LANGUAGE_EXTENSIONS = {
    "c": ".c",
    "c++": ".cpp",
    "cpp": ".cpp",
    "csharp": ".cs",
    "c#": ".cs",
    "golang": ".go",
    "go": ".go",
    "java": ".java",
    "javascript": ".js",
    "js": ".js",
    "kotlin": ".kt",
    "mysql": ".sql",
    "mssql": ".sql",
    "oraclesql": ".sql",
    "pandas": ".py",
    "php": ".php",
    "python": ".py",
    "python3": ".py",
    "ruby": ".rb",
    "rust": ".rs",
    "scala": ".scala",
    "swift": ".swift",
    "typescript": ".ts",
    "ts": ".ts",
}


class LocalLeetCodeError(Exception):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_command(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
    )


def command_or_error(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = run_command(args, cwd=cwd)
    if result.returncode != 0:
        output = "\n".join(
            part for part in [result.stdout.strip(), result.stderr.strip()] if part
        )
        raise LocalLeetCodeError(f"{' '.join(args)} failed:\n{output}")
    return result


def load_or_create_token(root: Path) -> str:
    env_token = os.environ.get("LOCAL_LEETCODE_TOKEN", "").strip()
    if env_token:
        return env_token

    token_path = root / "automation" / TOKEN_FILE
    if token_path.is_file():
        with token_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        token = str(data.get("token", "")).strip()
        if token:
            return token

    token = secrets.token_urlsafe(32)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with token_path.open("w", encoding="utf-8") as handle:
        json.dump({"token": token}, handle, indent=2)
        handle.write("\n")
    return token


def clean_topic(topic: Any) -> str:
    value = str(topic).strip()
    if not value:
        raise LocalLeetCodeError("topic names cannot be empty")
    return value


def clean_topics(topics: Any) -> list[str]:
    if not isinstance(topics, list):
        raise LocalLeetCodeError("topics must be a list")

    cleaned: list[str] = []
    seen: set[str] = set()
    for topic in topics:
        value = clean_topic(topic)
        if value not in seen:
            cleaned.append(value)
            seen.add(value)

    if not cleaned:
        raise LocalLeetCodeError("at least one topic is required")
    return cleaned


def normalize_difficulty(value: Any) -> str:
    difficulty = str(value).strip().lower()
    if difficulty not in VALID_DIFFICULTIES:
        raise LocalLeetCodeError("difficulty must be easy, medium, or hard")
    return difficulty


def normalize_slug(value: Any) -> str:
    slug = str(value).strip().lower()
    if not SLUG_RE.match(slug):
        raise LocalLeetCodeError(f"invalid LeetCode slug: {slug}")
    return slug


def problem_folder_name(frontend_id: Any, slug: str) -> str:
    frontend_id_text = str(frontend_id).strip()
    if not frontend_id_text.isdigit():
        raise LocalLeetCodeError("problem frontend id must be numeric")
    return f"{int(frontend_id_text):04d}-{slug}"


def language_extension(language: Any, lang_slug: Any) -> str:
    candidates = [str(lang_slug or "").strip().lower(), str(language or "").strip().lower()]
    for candidate in candidates:
        if candidate in LANGUAGE_EXTENSIONS:
            return LANGUAGE_EXTENSIONS[candidate]
    raise LocalLeetCodeError(
        f"unsupported language: {language or lang_slug}; add it to LANGUAGE_EXTENSIONS"
    )


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    problem = payload.get("problem")
    if not isinstance(problem, dict):
        raise LocalLeetCodeError("payload.problem must be an object")

    slug = normalize_slug(problem.get("slug") or problem.get("titleSlug"))
    folder = problem_folder_name(problem.get("frontendId"), slug)
    if not PROBLEM_FOLDER_RE.match(folder):
        raise LocalLeetCodeError(f"invalid problem folder: {folder}")

    difficulty = normalize_difficulty(problem.get("difficulty"))
    topics = clean_topics(problem.get("topics"))
    extension = language_extension(payload.get("language"), payload.get("langSlug"))

    code = str(payload.get("code") or "").replace("\r\n", "\n")
    if not code.strip():
        raise LocalLeetCodeError("solution code cannot be empty")

    readme = str(payload.get("readmeContent") or "").replace("\r\n", "\n")
    if not readme.strip():
        raise LocalLeetCodeError("README content cannot be empty")

    commit_message = str(payload.get("commitMessage") or "").strip()
    if not commit_message:
        raise LocalLeetCodeError("commit message cannot be empty")

    return {
        "folder": folder,
        "difficulty": difficulty,
        "topics": topics,
        "extension": extension,
        "code": code.rstrip() + "\n",
        "readme": readme.rstrip() + "\n",
        "commitMessage": commit_message,
        "overwrite": bool(payload.get("overwrite")),
    }


def existing_solution_files(problem_dir: Path) -> list[str]:
    if not problem_dir.is_dir():
        return []
    return sorted(
        child.name
        for child in problem_dir.iterdir()
        if child.is_file() and child.suffix.lower() in SOLUTION_EXTENSIONS
    )


def preview_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_payload(payload)
    folder = normalized["folder"]
    problem_dir = root / folder
    solution_file = f"{folder}{normalized['extension']}"
    return {
        "problemFolder": folder,
        "exists": problem_dir.exists(),
        "solutionPath": f"{folder}/{solution_file}",
        "readmePath": f"{folder}/README.md",
        "existingFiles": sorted(child.name for child in problem_dir.iterdir())
        if problem_dir.is_dir()
        else [],
        "existingSolutionFiles": existing_solution_files(problem_dir),
        "difficulty": normalized["difficulty"],
        "topics": normalized["topics"],
        "commitMessage": normalized["commitMessage"],
    }


def canonicalize_readme(problem_dir: Path) -> None:
    if not problem_dir.is_dir():
        return

    for child in problem_dir.iterdir():
        if child.is_file() and child.name.lower() == "readme.md" and child.name != "README.md":
            temp = problem_dir / "README.__tmp__"
            target = problem_dir / "README.md"
            child.rename(temp)
            temp.rename(target)
            return


def write_problem_files(root: Path, normalized: dict[str, Any]) -> None:
    folder = normalized["folder"]
    problem_dir = root / folder
    exists = problem_dir.exists()
    if exists and not normalized["overwrite"]:
        raise LocalLeetCodeError(f"{folder} already exists; confirm overwrite first")

    problem_dir.mkdir(parents=True, exist_ok=True)
    canonicalize_readme(problem_dir)

    solution_name = f"{folder}{normalized['extension']}"
    solution_path = problem_dir / solution_name

    for old_solution in existing_solution_files(problem_dir):
        if old_solution != solution_name:
            (problem_dir / old_solution).unlink()

    solution_path.write_text(normalized["code"], encoding="utf-8")
    (problem_dir / "README.md").write_text(normalized["readme"], encoding="utf-8")


def sync_stats(root: Path, normalized: dict[str, Any]) -> list[str]:
    command = [
        sys.executable,
        "sync_stats.py",
        "--write",
        "--problem",
        normalized["folder"],
        "--difficulty",
        normalized["difficulty"],
        "--topics",
        *normalized["topics"],
    ]
    write_result = command_or_error(command, cwd=root)
    check_result = command_or_error([sys.executable, "sync_stats.py", "--check"], cwd=root)
    return [write_result.stdout.strip(), check_result.stdout.strip()]


def commit_changes(root: Path, normalized: dict[str, Any]) -> dict[str, Any]:
    folder = normalized["folder"]
    pathspecs = [folder, "README.md", "stats.json"]

    command_or_error(["git", "add", "--", *pathspecs], cwd=root)
    diff_result = run_command(["git", "diff", "--cached", "--quiet", "--", *pathspecs], cwd=root)
    if diff_result.returncode == 0:
        return {"committed": False, "message": "No staged changes for this problem."}
    if diff_result.returncode != 1:
        output = "\n".join(
            part for part in [diff_result.stdout.strip(), diff_result.stderr.strip()] if part
        )
        raise LocalLeetCodeError(f"git diff --cached failed:\n{output}")

    result = command_or_error(
        ["git", "commit", "-m", normalized["commitMessage"], "--", *pathspecs],
        cwd=root,
    )
    return {"committed": True, "message": result.stdout.strip()}


def save_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_payload(payload)
    preview = preview_payload(root, payload)
    write_problem_files(root, normalized)
    sync_output = sync_stats(root, normalized)
    commit = commit_changes(root, normalized)
    return {
        "ok": True,
        "preview": preview,
        "syncOutput": sync_output,
        "commit": commit,
    }


class LocalLeetCodeHandler(BaseHTTPRequestHandler):
    server_version = "LocalLeetCodeServer/0.1"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", f"Content-Type, {TOKEN_HEADER}")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/health":
            self.write_json({"ok": False, "error": "not found"}, status=404)
            return
        self.write_json(
            {
                "ok": True,
                "repoRoot": str(self.server.repo_root),
                "tokenHeader": TOKEN_HEADER,
            }
        )

    def do_POST(self) -> None:
        try:
            self.require_token()
            payload = self.read_payload()
            parsed = urlparse(self.path)
            if parsed.path == "/preview":
                self.write_json({"ok": True, "preview": preview_payload(self.server.repo_root, payload)})
            elif parsed.path == "/save":
                self.write_json(save_payload(self.server.repo_root, payload))
            else:
                self.write_json({"ok": False, "error": "not found"}, status=404)
        except LocalLeetCodeError as exc:
            self.write_json({"ok": False, "error": str(exc)}, status=400)
        except json.JSONDecodeError as exc:
            self.write_json({"ok": False, "error": f"invalid JSON: {exc}"}, status=400)
        except Exception as exc:
            self.write_json({"ok": False, "error": f"unexpected error: {exc}"}, status=500)

    def require_token(self) -> None:
        supplied = self.headers.get(TOKEN_HEADER, "")
        if not secrets.compare_digest(supplied, self.server.token):
            raise LocalLeetCodeError("invalid or missing local token")

    def read_payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise LocalLeetCodeError("request body is required")
        data = self.rfile.read(length).decode("utf-8")
        payload = json.loads(data)
        if not isinstance(payload, dict):
            raise LocalLeetCodeError("request body must be a JSON object")
        return payload

    def write_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("local-leetcode: " + format % args + "\n")


class LocalLeetCodeServer(ThreadingHTTPServer):
    repo_root: Path
    token: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local helper used by the Local LeetCode Sync extension."
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    token = load_or_create_token(root)
    server = LocalLeetCodeServer((HOST, args.port), LocalLeetCodeHandler)
    server.repo_root = root
    server.token = token

    print(f"Local LeetCode server listening on http://{HOST}:{args.port}")
    print(f"Repo root: {root}")
    print(f"Extension token: {token}")
    print("Keep this window open while saving from LeetCode. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local LeetCode server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
