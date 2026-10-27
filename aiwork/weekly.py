"""주간 루틴 — 이번 주에 할 일을 한 번에 모아 준다 (SPEC 10절).

스케줄로 뜬 Claude 가 이 결과를 읽고 글을 쓴다.
    1. 변경 있는 프로젝트 → 개발 일지 후보 (커밋이 기준 미만이면 뺀다. 억지로 채우면 변경 로그가 된다)
    2. 사례 큐의 다음 '대기' 1건 → 사례 글 후보
    3. 워크북 원고의 경험담 플레이스홀더 수와 게시된 편 → 다음 편을 낼 수 있는지
    4. 지난 실행 이후 새 댓글 → 답글 대상
마지막 실행 시각은 ~/.aiwork/state.json 에 남긴다.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import check, collect, comments, content, terms as terms_mod
from .config import Config, config_dir

MIN_COMMITS = 3
STAGES = ("analysis", "design", "build", "test", "deploy", "operate")


def _stage_posts(config: Config, project: str) -> dict:
    mine = content.list_posts(config, project=project, status="published")
    return {s: sum(1 for p in mine if p["kind"] == s) for s in STAGES}


def _next_stage(config: Config, project: str) -> str:
    counts = _stage_posts(config, project)
    return next((s for s in STAGES if counts[s] == 0), "operate")
STATE_FILE = "state.json"


def _state_path() -> Path:
    return config_dir() / STATE_FILE


def load_state() -> dict:
    p = _state_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict) -> None:
    _state_path().write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def gather(config: Config, min_commits: int = MIN_COMMITS, sample: int = 15) -> dict:
    state = load_state()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # 1. 프로젝트
    cards = {c["slug"]: c for c in content.list_project_cards(config)}
    ready, skipped = [], []
    for project in config.projects:
        if not project.public or not collect.is_repo(project.path):
            skipped.append({"project": project.name, "reason": "비공개 또는 git 아님"})
            continue
        last = content.last_published(config, project.name)
        since = last.until_commit if last else None
        n = collect.count_since(project, since)
        # 개발 주기 여섯 단계가 아직 다 안 나온 프로젝트는 커밋이 없어도 다음 단계 글을 쓴다 —
        # 분석·설계·개발 글은 이미 있는 SPEC 과 기록이 재료라서 새 커밋이 필요 없다.
        cycle_done = _next_stage(config, project.name) == "operate" and _stage_posts(config, project.name)["operate"] > 0
        if n < min_commits and cycle_done:
            skipped.append({"project": project.name, "reason": f"이후 커밋 {n}건 (기준 {min_commits} 미만)"})
            continue
        changes = collect.get_changes(project, since=since, limit=sample)
        ready.append({
            "project": project.name, "since": since,
            "last_post": {"title": last.title, "date": last.date.isoformat() if last.date else None} if last else None,
            # 개발 주기에서 아직 글이 없는 첫 단계. 여섯 단계가 다 있으면 운영을 회차처럼 이어 간다.
            "next_stage": _next_stage(config, project.name),
            "stage_posts": _stage_posts(config, project.name),
            # 글이 가는 주제와 연재 이름. 카드에 topic 이 있으면 그쪽(장기 연재), 없으면 made.
            "topic": cards.get(project.name, {}).get("topic", "made"),
            "series": cards.get(project.name, {}).get("series"),
            "commits_since": n, "head": collect.head(project),
            "recent": [{"hash": c["hash"], "date": c["date"][:10], "subject": c["subject"]} for c in changes["commits"]],
            "docs": collect.list_docs(project),
        })

    # 2. 큐
    waiting = content.list_queue(config, status="대기")
    next_case = waiting[0] if waiting else None

    # 3. 워크북
    workbook = []
    for s in config.sources:
        for rel in [p.relative_to(s.path).as_posix() for p in sorted(s.path.glob("*.md")) if p.name.lower() != "readme.md"]:
            text = (s.path / rel).read_text(encoding="utf-8", errors="replace")
            placeholders = text.count(check.PLACEHOLDER)
            workbook.append({"source": s.name, "topic": s.topic, "doc": rel, "placeholders": placeholders})
    published_parts = content.list_posts(config, kind="workbook", status="published")

    # 4. 댓글
    new_comments: list[dict] | None = None
    comments_note = None
    if config.comments.enabled:
        try:
            rows = comments.list_comments(config, since=state.get("last_run"))["comments"]
            new_comments = [r for r in rows if not r.get("replied")]
        except Exception as e:  # 네트워크 실패로 주간 실행 전체가 죽지 않게
            comments_note = f"댓글 조회 실패: {e}"
    else:
        comments_note = "[comments] 설정이 비어 있다."

    digests = content.list_posts(config, kind="digest", status="published")

    return {
        "generated_at": now,
        "weekly_ai": {"feeds": [f.name for f in config.feeds], "published": len(digests), "next_order": len(digests) + 1},
        "last_run": state.get("last_run"),
        "projects": {"ready": ready, "skipped": skipped},
        "next_case": next_case,
        "queue_waiting": len(waiting),
        "workbook": {"sources": workbook, "published_parts": len(published_parts)},
        "comments": {"new": new_comments, "note": comments_note},
        "terms": {"count": len(terms_mod.list_terms(config)),
                  "names": [t["term"] for t in terms_mod.list_terms(config)]},
    }


def mark_run(now: str | None = None) -> None:
    state = load_state()
    state["last_run"] = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_state(state)


def render(result: dict) -> str:
    out = [f"# 이번 주 할 일 ({result['generated_at'][:10]})", ""]
    ready = result["projects"]["ready"]
    out.append(f"## 1. 프로젝트 글 후보 {len(ready)}건")
    for r in ready:
        out.append(f"- {r['project']}: {r['suggested_kind']}, 이후 커밋 {r['commits_since']}건 (since {r['since'] or '처음'}, HEAD {r['head']})")
        for c in r["recent"][:8]:
            out.append(f"    {c['hash']} {c['date']} {c['subject']}")
    for s in result["projects"]["skipped"]:
        out.append(f"- (건너뜀) {s['project']}: {s['reason']}")
    out.append("")
    nc = result["next_case"]
    out.append(f"## 2. 사례 큐 (대기 {result['queue_waiting']}건)")
    out.append(f"- 다음: {nc['id']} — {nc['audience']} / {nc['task']} / 질문: {nc['question']}" if nc else "- 대기 중인 사례가 없다. 큐에 직군×업무를 추가한다.")
    out.append("")
    wb = result["workbook"]
    out.append(f"## 3. 워크북 (게시된 편 {wb['published_parts']})")
    for w in wb["sources"]:
        flag = "경험담 자리가 남아 있어 못 낸다" if w["placeholders"] else "플레이스홀더 없음 — 다음 편을 낼 수 있다"
        out.append(f"- {w['source']}/{w['doc']}: 플레이스홀더 {w['placeholders']}개 → {flag}")
    out.append("")
    wa = result.get("weekly_ai", {})
    out.append(f"## 5. Weekly AI (게시 {wa.get('published', 0)}편, 다음 {wa.get('next_order', 1)}주차) — 피드 {', '.join(wa.get('feeds', [])) or '없음'}")
    out.append("")
    cm = result["comments"]
    if cm["new"] is None:
        out.append(f"## 4. 댓글 — {cm['note']}")
    else:
        out.append(f"## 4. 새 댓글 {len(cm['new'])}건 (지난 실행 {result['last_run'] or '없음'} 이후)")
        for c in cm["new"]:
            out.append(f"- #{c['id']} [{c['post']}] {c['body'][:80]}")
    return "\n".join(out)
