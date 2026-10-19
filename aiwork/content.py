"""사이트 콘텐츠 읽기 — 주제, 프로젝트 카드, 글, 초안, 사례 큐.

상태를 담는 DB 는 없다. 파일이 어느 폴더에 있느냐가 곧 상태다.
    drafts/              → 초안
    src/content/posts/   → 게시됨 (draft: true 면 내려진 글)
큐는 src/content/queue/<topic>.yaml 한 파일이고, status 가 대기/작성중/게시 로 바뀐다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import yaml

from .config import Config, Source
from .collect import read_text_within


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    return (meta if isinstance(meta, dict) else {}), parts[2].lstrip("\n")


def _as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


# ── 주제·프로젝트 카드 ────────────────────────────────────────────────


def _cards(folder: Path) -> list[dict]:
    out = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.glob("*.md")):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        meta["slug"] = path.stem
        out.append(meta)
    out.sort(key=lambda m: (m.get("order", 99), m["slug"]))
    return out


def list_topics(config: Config) -> list[dict]:
    posts = all_posts(config)
    queue = all_queue(config)
    rows = []
    for t in _cards(config.site.topics):
        mine = [p for p in posts if p.topic == t["slug"] and p.status == "published"]
        rows.append({
            "slug": t["slug"],
            "name": t.get("name"),
            "summary": t.get("summary"),
            "post_count": len(mine),
            "last_post_date": max((p.date for p in mine if p.date), default=None).isoformat()
            if any(p.date for p in mine) else None,
            "queue_waiting": sum(1 for q in queue if q.get("topic") == t["slug"] and q.get("status") == "대기"),
        })
    return rows


def list_project_cards(config: Config) -> list[dict]:
    return _cards(config.site.project_cards)


# ── 글 ────────────────────────────────────────────────────────────────


@dataclass
class Post:
    id: str
    title: str
    date: date | None
    topic: str | None
    kind: str | None
    project: str | None
    audience: str | None
    series: str | None
    order: int | None
    until_commit: str | None
    queue_id: str | None
    status: str  # draft | published | unpublished
    path: Path

    def as_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title,
            "date": self.date.isoformat() if self.date else None,
            "topic": self.topic, "kind": self.kind, "project": self.project,
            "audience": self.audience, "series": self.series, "order": self.order,
            "until_commit": self.until_commit, "queue_id": self.queue_id,
            "status": self.status,
        }


def _read_post(path: Path, base: Path, status: str) -> Post | None:
    try:
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    if status == "published" and meta.get("draft") is True:
        status = "unpublished"
    rel = path.relative_to(base).with_suffix("").as_posix()
    return Post(
        id=rel, title=str(meta.get("title") or path.stem), date=_as_date(meta.get("date")),
        topic=meta.get("topic"), kind=meta.get("kind"), project=meta.get("project"),
        audience=meta.get("audience"), series=meta.get("series"), order=meta.get("order"),
        until_commit=meta.get("until_commit"), queue_id=meta.get("queue_id"),
        status=status, path=path,
    )


def all_posts(config: Config) -> list[Post]:
    found: list[Post] = []
    for folder, status in ((config.site.posts, "published"), (config.site.drafts, "draft")):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("**/*.md")):
            post = _read_post(path, folder, status)
            if post:
                found.append(post)
    found.sort(key=lambda p: (p.date or date.min), reverse=True)
    return found


def list_posts(config: Config, topic: str | None = None, kind: str | None = None,
               project: str | None = None, status: str | None = None) -> list[dict]:
    posts = all_posts(config)
    if topic:
        posts = [p for p in posts if p.topic == topic]
    if kind:
        posts = [p for p in posts if p.kind == kind]
    if project:
        posts = [p for p in posts if p.project == project]
    if status:
        posts = [p for p in posts if p.status == status]
    return [p.as_dict() for p in posts]


def last_published(config: Config, project: str) -> Post | None:
    """그 프로젝트로 마지막에 게시된 글. 다음 개발 일지의 시작점."""
    for post in all_posts(config):
        if post.status == "published" and post.project == project:
            return post
    return None


# ── 사례 큐 ───────────────────────────────────────────────────────────


def all_queue(config: Config) -> list[dict]:
    items: list[dict] = []
    if not config.site.queue.is_dir():
        return items
    for path in sorted(config.site.queue.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for row in data:
            row.setdefault("topic", path.stem)
            row.setdefault("status", "대기")
            items.append(row)
    return items


def list_queue(config: Config, topic: str | None = None, status: str | None = None) -> list[dict]:
    rows = all_queue(config)
    if topic:
        rows = [r for r in rows if r.get("topic") == topic]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return rows


# ── 원고 폴더 ─────────────────────────────────────────────────────────


def list_sources(config: Config, topic: str | None = None) -> list[dict]:
    """등록된 원고 폴더와 그 안의 md 문서."""
    rows = []
    for s in config.sources:
        if topic and s.topic != topic:
            continue
        docs = [p.relative_to(s.path).as_posix() for p in sorted(s.path.rglob("*.md"))
                if ".git" not in p.parts and "node_modules" not in p.parts]
        rows.append({"name": s.name, "topic": s.topic, "docs": docs[:100]})
    return rows


def read_source(source: Source, relative: str) -> dict:
    content, truncated = read_text_within(source.path, relative)
    return {"source": source.name, "topic": source.topic, "path": relative,
            "content": content, "truncated": truncated}
