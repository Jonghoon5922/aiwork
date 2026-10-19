"""게시 — 사이트 저장소를 커밋하고 push 한다. push 가 곧 배포다.

커밋 대상은 콘텐츠 폴더(src/content)뿐이다. 코드 변경은 사람이 커밋한다.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime

from .config import Config

CONTENT_DIR = "src/content"


def _git(config: Config, *args: str) -> tuple[int, str]:
    done = subprocess.run(
        ["git", "-C", str(config.site.path), "-c", "core.quotepath=false", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    # strip() 을 하면 porcelain 첫 줄의 앞 공백(" M path")이 날아가 경로 첫 글자가 잘린다. 끝만 자른다.
    return done.returncode, (done.stdout + done.stderr).rstrip()


def state(config: Config) -> dict:
    rc, branch = _git(config, "rev-parse", "--abbrev-ref", "HEAD")
    branch = branch.strip()
    _, dirty = _git(config, "status", "--porcelain", "--", CONTENT_DIR)
    _, ahead = _git(config, "rev-list", "--count", "@{u}..HEAD")
    ahead = ahead.strip()
    return {
        "branch": branch if rc == 0 else None,
        "content_dirty": [line[3:] for line in dirty.splitlines() if line.strip()],
        "unpushed_commits": int(ahead) if ahead.isdigit() else None,
    }


def publish(config: Config, message: str | None = None, push: bool = True) -> dict:
    """src/content 의 변경을 커밋하고 push 한다. 변경이 없으면 아무것도 하지 않는다."""
    before = state(config)
    if not before["content_dirty"]:
        return {"published": False, "note": "콘텐츠 변경이 없다.", **before}

    rc, out = _git(config, "add", "--", CONTENT_DIR)
    if rc != 0:
        return {"published": False, "note": f"git add 실패: {out}"}

    msg = message or f"글 게시 {datetime.now():%Y-%m-%d %H:%M}"
    rc, out = _git(config, "commit", "-q", "-m", msg)
    if rc != 0:
        return {"published": False, "note": f"git commit 실패: {out}"}
    _, sha = _git(config, "rev-parse", "--short", "HEAD")
    sha = sha.strip()

    pushed = False
    note = "커밋했다. push 는 하지 않았다."
    if push:
        rc, out = _git(config, "push", "-q", "origin", "HEAD")
        pushed = rc == 0
        note = "push 했다. Actions 가 빌드하면 사이트에 올라간다. deploy_status 로 확인한다." if pushed else f"push 실패: {out}"

    return {"published": pushed, "commit": sha, "files": before["content_dirty"], "note": note}


def _repo_slug(config: Config) -> str | None:
    rc, url = _git(config, "remote", "get-url", "origin")
    if rc != 0:
        return None
    url = url.strip().removesuffix(".git")
    for prefix in ("https://github.com/", "git@github.com:"):
        if url.startswith(prefix):
            return url[len(prefix):]
    return None


def deploy_status(config: Config, limit: int = 3) -> dict:
    """GitHub Actions 최근 실행. gh 가 있어야 한다."""
    slug = _repo_slug(config)
    if not slug:
        return {"available": False, "note": "origin 이 GitHub 가 아니다."}
    try:
        done = subprocess.run(
            ["gh", "api", f"repos/{slug}/actions/runs?per_page={limit}",
             "-q", ".workflow_runs[] | {status, conclusion, head_sha: .head_sha[0:7], created_at, html_url, title: .display_title}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        )
    except FileNotFoundError:
        return {"available": False, "note": "gh 명령이 없어 배포 상태를 알 수 없다."}
    if done.returncode != 0:
        return {"available": False, "note": (done.stderr or "gh 실행 실패").strip()}
    runs = [json.loads(line) for line in done.stdout.splitlines() if line.strip()]
    latest = runs[0] if runs else None
    return {
        "available": True, "runs": runs,
        "note": (f"최근 실행: {latest['status']}/{latest['conclusion']} ({latest['head_sha']})" if latest else "실행 기록 없음"),
    }
