"""원고 — 초안 저장, 승인, 수정, 내리기.

상태 전이는 파일 이동이다.
    save_draft  →  drafts/<topic>/<slug>.md
    approve     →  drafts/ → src/content/posts/<topic>/<slug>.md   (check 통과 필수, 큐 상태 갱신)
    unpublish   →  posts 의 글에 draft: true 를 박는다 (파일은 남긴다 — 주소를 잃지 않게)
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml

from . import check, collect, content
from .config import AccessDenied, Config

STAGES = ("analysis", "design", "build", "test", "deploy", "operate")
KINDS = ("workbook", "case", *STAGES, "decision", "journal")

_SLUG_STRIP = re.compile(r"[^0-9A-Za-z가-힣\s-]")
_SLUG_SPACE = re.compile(r"\s+")

# 프론트매터 순서. 흔들리면 diff 가 지저분해진다.
_ORDER = ("title", "question", "date", "topic", "kind", "audience", "series", "order",
          "project", "until_commit", "summary", "materials", "faq", "tags", "queue_id", "draft")


def make_slug(title: str) -> str:
    text = _SLUG_STRIP.sub("", title).strip()
    text = _SLUG_SPACE.sub("-", text)
    return text[:60].strip("-") or "글"


def _frontmatter(meta: dict) -> str:
    ordered = {k: meta[k] for k in _ORDER if k in meta and meta[k] not in (None, "", [])}
    dumped = yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False, default_flow_style=None, width=1000)
    return "---\n" + dumped + "---"


def _write(path: Path, meta: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_frontmatter(meta) + "\n\n" + body.strip() + "\n", encoding="utf-8")


def _validate_topic(config: Config, topic: str) -> None:
    slugs = [t["slug"] for t in content.list_topics(config)]
    if topic not in slugs:
        raise AccessDenied(f"'{topic}' 은 없는 주제다. 있는 것: {', '.join(slugs)}")


def save_draft(config: Config, topic: str, kind: str, title: str, body: str, summary: str,
               question: str | None = None, audience: str | None = None, series: str | None = None,
               order: int | None = None, project: str | None = None, until_commit: str | None = None,
               materials: str | None = None, faq: list[dict] | None = None, tags: list[str] | None = None,
               queue_id: str | None = None, slug: str | None = None) -> dict:
    """초안을 drafts/<topic>/ 에 만들고 곧바로 검사한다. 저장소에는 올라가지 않는다."""
    _validate_topic(config, topic)
    if kind not in KINDS:
        raise AccessDenied(f"kind 는 {', '.join(KINDS)} 중 하나다.")
    if kind in (*STAGES, "decision", "journal"):
        if not project:
            raise AccessDenied(f"kind={kind} 는 project 가 필요하다.")
        proj = config.project(project)
        proj.require_public()
        if not until_commit:
            until_commit = collect.head(proj)
    if kind == "case" and not audience:
        raise AccessDenied("kind=case 는 audience(직군) 가 필요하다.")
    if kind in ("workbook", "journal") and (series is None or order is None):
        raise AccessDenied(f"kind={kind} 은 series 와 order 가 필요하다.")

    slug = slug or make_slug(title)
    path = config.site.drafts / topic / f"{slug}.md"
    if path.exists() or (config.site.posts / topic / f"{slug}.md").exists():
        raise AccessDenied(f"같은 slug 의 글이 이미 있다: {topic}/{slug}")

    meta = {
        "title": title, "question": question, "date": date.today().isoformat(), "topic": topic, "kind": kind,
        "audience": audience, "series": series, "order": order, "project": project, "until_commit": until_commit,
        "summary": summary, "materials": materials, "faq": faq or [], "tags": tags or [], "queue_id": queue_id,
    }
    _write(path, meta, body)
    result = check.check_file(path, config)
    result["id"] = f"{topic}/{slug}"
    result["path"] = str(path.relative_to(config.site.path))
    return result


def _find(config: Config, post_id: str) -> tuple[Path, str]:
    """id(topic/slug) 로 초안이나 글을 찾는다."""
    rel = post_id if post_id.endswith(".md") else post_id + ".md"
    for folder, status in ((config.site.drafts, "draft"), (config.site.posts, "published")):
        candidate = folder / rel
        if candidate.exists():
            return candidate, status
    raise AccessDenied(f"없는 글이다: {post_id}")


def approve(config: Config, draft_id: str) -> dict:
    """check 통과를 확인하고 drafts/ → posts/ 로 옮긴다. 큐에 연결된 글이면 큐 상태를 '게시' 로."""
    path, status = _find(config, draft_id)
    if status != "draft":
        raise AccessDenied(f"초안이 아니다: {draft_id}")
    result = check.check_file(path, config)
    if not result["ok"]:
        raise AccessDenied(f"check 를 통과하지 못했다 ({result['blocking']}건). approve 할 수 없다.")

    meta, body = content.split_frontmatter(path.read_text(encoding="utf-8"))
    meta["date"] = date.today().isoformat()
    meta.pop("draft", None)
    target = config.site.posts / path.relative_to(config.site.drafts)
    _write(target, meta, body)
    path.unlink()

    queue_note = None
    if meta.get("queue_id"):
        queue_note = _set_queue_status(config, meta["queue_id"], "게시")
    return {"id": draft_id, "path": str(target.relative_to(config.site.path)), "moved": True,
            "warnings": result["warnings"], "queue": queue_note,
            "note": "posts/ 로 옮겼다. publish 로 push 하면 사이트에 올라간다."}


def _set_queue_status(config: Config, queue_id: str, status: str) -> str | None:
    for qpath in sorted(config.site.queue.glob("*.yaml")):
        text = qpath.read_text(encoding="utf-8")
        rows = yaml.safe_load(text) or []
        hit = False
        for row in rows:
            if row.get("id") == queue_id:
                row["status"] = status
                hit = True
        if hit:
            # 주석을 잃지 않으려고 통째로 덤프하지 않고, 해당 id 블록의 status 줄만 바꾼다.
            new = re.sub(
                rf"(- id: {re.escape(queue_id)}\n(?:  .*\n)*?  status: )\S+",
                rf"\g<1>{status}", text,
            )
            qpath.write_text(new, encoding="utf-8")
            return f"{queue_id} → {status}"
    return None


def update_post(config: Config, post_id: str, body: str | None = None, title: str | None = None,
                summary: str | None = None, question: str | None = None, tags: list[str] | None = None,
                faq: list[dict] | None = None) -> dict:
    """글이나 초안을 고친다. 고친 뒤 곧바로 검사한다. 게시된 글은 publish 를 다시 해야 반영된다."""
    path, status = _find(config, post_id)
    meta, old_body = content.split_frontmatter(path.read_text(encoding="utf-8"))
    for key, value in (("title", title), ("summary", summary), ("question", question), ("tags", tags), ("faq", faq)):
        if value is not None:
            meta[key] = value
    _write(path, meta, body if body is not None else old_body)
    result = check.check_file(path, config)
    result["id"] = post_id
    result["status"] = status
    return result


def unpublish(config: Config, post_id: str) -> dict:
    """게시된 글에 draft: true 를 박아 사이트에서 내린다. publish 로 push 해야 실제로 내려간다."""
    path, status = _find(config, post_id)
    if status != "published":
        raise AccessDenied(f"게시된 글이 아니다: {post_id}")
    meta, body = content.split_frontmatter(path.read_text(encoding="utf-8"))
    meta["draft"] = True
    _write(path, meta, body)
    return {"id": post_id, "unpublished": True, "note": "draft: true 로 바꿨다. publish 로 push 하면 사이트에서 내려간다."}
