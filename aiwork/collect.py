"""프로젝트 재료 — git 기록과 프로젝트 문서를 읽는다.

읽기 전용이다. 어떤 프로젝트 폴더에도 쓰지 않는다.
GitPython 대신 subprocess 로 git 을 부른다. 의존을 하나 줄이고 출력 형식을 우리가 정한다.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import AccessDenied, Project, resolve_within

_REC = "\x1e"
_SEP = "\x1f"

DIFF_LIMIT = 60_000
DOC_LIMIT = 200_000


class GitError(Exception):
    """git 명령이 실패했다."""


@dataclass
class Commit:
    hash: str
    short: str
    date: str
    subject: str
    files: list[str]

    def as_dict(self) -> dict:
        return {
            "hash": self.short,
            "full_hash": self.hash,
            "date": self.date,
            "subject": self.subject,
            "files": self.files,
        }


def _git(root: Path, *args: str) -> str:
    try:
        done = subprocess.run(
            # core.quotepath=false 가 없으면 한글 파일명이 8진 이스케이프로 나온다.
            ["git", "-C", str(root), "-c", "core.quotepath=false", *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("git 을 찾을 수 없다.") from exc
    if done.returncode != 0:
        raise GitError((done.stderr or done.stdout).strip() or "git 명령이 실패했다.")
    return done.stdout


def is_repo(root: Path) -> bool:
    try:
        return _git(root, "rev-parse", "--is-inside-work-tree").strip() == "true"
    except GitError:
        return False


def head(project: Project) -> str | None:
    try:
        return _git(project.path, "rev-parse", "--short", "HEAD").strip()
    except GitError:
        return None


def count_since(project: Project, since: str | None) -> int:
    """since 이후 커밋 수. since 가 이 저장소에 없는 커밋이면 0."""
    if not is_repo(project.path):
        return 0
    try:
        rev = f"{since}..HEAD" if since else "HEAD"
        return int(_git(project.path, "rev-list", "--count", rev).strip() or 0)
    except (GitError, ValueError):
        return 0


def _looks_like_rev(project: Project, value: str) -> bool:
    try:
        _git(project.path, "rev-parse", "--verify", "--quiet", f"{value}^{{commit}}")
        return True
    except GitError:
        return False


def _parse_log(out: str) -> list[Commit]:
    commits: list[Commit] = []
    for chunk in out.split(_REC):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        header, _, rest = chunk.partition("\n")
        parts = header.split(_SEP)
        if len(parts) < 4:
            continue
        files = [line for line in rest.splitlines() if line.strip()]
        commits.append(Commit(hash=parts[0], short=parts[1], date=parts[2], subject=parts[3], files=files))
    return commits


def get_changes(project: Project, since: str | None = None, limit: int = 100) -> dict:
    """커밋 목록과 요약. since 는 커밋 해시나 날짜(2026-09-01)."""
    project.require_public()
    if not is_repo(project.path):
        raise GitError(f"'{project.name}' 는 git 저장소가 아니다: {project.path}")

    fmt = f"{_REC}%H{_SEP}%h{_SEP}%aI{_SEP}%s"
    args = ["log", f"--pretty=format:{fmt}", "--name-only", f"-{limit}"]
    if since:
        args.append(f"{since}..HEAD" if _looks_like_rev(project, since) else f"--since={since}")

    commits = _parse_log(_git(project.path, *args))
    touched: set[str] = set()
    for c in commits:
        touched.update(c.files)

    return {
        "project": project.name,
        "since": since,
        "commits": [c.as_dict() for c in commits],
        "summary": {
            "commit_count": len(commits),
            "file_count": len(touched),
            "first_date": commits[-1].date if commits else None,
            "last_date": commits[0].date if commits else None,
            "head": commits[0].short if commits else None,
        },
    }


def get_diff(project: Project, commit: str | None = None, path: str | None = None, limit: int = DIFF_LIMIT) -> dict:
    project.require_public()
    if not is_repo(project.path):
        raise GitError(f"'{project.name}' 는 git 저장소가 아니다.")
    if commit:
        args = ["show", "--patch", "--stat", commit] + (["--", path] if path else [])
    elif path:
        args = ["log", "--patch", "-10", "--", path]
    else:
        raise GitError("commit 이나 path 중 하나는 필요하다.")

    text = _git(project.path, *args)
    truncated = len(text) > limit
    return {
        "project": project.name, "commit": commit, "path": path,
        "diff": text[:limit], "truncated": truncated,
        "note": "너무 커서 잘랐다. 경로를 좁혀서 다시 요청한다." if truncated else None,
    }


def read_text_within(root: Path, relative: str, limit: int = DOC_LIMIT) -> tuple[str, bool]:
    """등록된 뿌리 안의 텍스트 파일을 읽는다. 원고 폴더와 프로젝트가 같이 쓴다."""
    target = resolve_within(root, relative)
    if not target.exists():
        raise AccessDenied(f"없는 파일이다: {relative}")
    if target.is_dir():
        raise AccessDenied(f"파일이 아니라 폴더다: {relative}")
    raw = target.read_bytes()
    if b"\x00" in raw[:4096]:
        raise AccessDenied(f"텍스트 파일이 아니다: {relative}")
    text = raw.decode("utf-8", errors="replace")
    return text[:limit], len(text) > limit


def read_doc(project: Project, relative: str) -> dict:
    project.require_public()
    content, truncated = read_text_within(project.path, relative)
    return {"project": project.name, "path": relative, "content": content, "truncated": truncated}


def list_docs(project: Project, limit: int = 60) -> list[str]:
    """프로젝트 뿌리의 md 문서와 docs/·design/·.claude/ 아래 문서."""
    project.require_public()
    names = [p.name for p in sorted(project.path.glob("*.md"))]
    for extra in ("docs", "design", ".claude"):
        d = project.path / extra
        if d.is_dir():
            names += [f"{extra}/{p.relative_to(d).as_posix()}" for p in sorted(d.rglob("*.md"))]
    return names[:limit]
