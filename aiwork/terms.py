"""용어집 — 용어 하나가 src/content/terms/<slug>.md 하나.

용어는 초안 단계가 없다. save_term 이 바로 쓰고 곧바로 검사해, block 이 있으면 파일을 지우고 결과만 돌려준다.
저장소에는 publish 가 올린다 (src/content 전체를 커밋한다).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from . import check, content
from .config import AccessDenied, Config

_SLUG = re.compile(r"[^a-z0-9-]")


def _folder(config: Config) -> Path:
    return config.site.path / "src" / "content" / "terms"


def list_terms(config: Config) -> list[dict]:
    """등록된 용어 전부 — slug, term, aliases, short."""
    rows = []
    for p in sorted(_folder(config).glob("*.md")):
        meta, _ = content.split_frontmatter(p.read_text(encoding="utf-8"))
        rows.append({"slug": p.stem, "term": meta.get("term"), "aliases": meta.get("aliases") or [],
                     "short": meta.get("short")})
    return rows


def _exists(config: Config, term: str, aliases: list[str]) -> str | None:
    names = {n.lower() for n in [term, *aliases]}
    for t in list_terms(config):
        have = {n.lower() for n in [t["term"], *t["aliases"]]}
        if names & have:
            return t["slug"]
    return None


def save_term(config: Config, slug: str, term: str, short: str, body: str,
              aliases: list[str] | None = None) -> dict:
    """용어 페이지를 만든다. slug 는 영문 소문자·숫자·하이픈. 이미 있는 용어(별칭 포함)면 거부."""
    slug = slug.strip().lower()
    if not slug or _SLUG.search(slug):
        raise AccessDenied("slug 는 영문 소문자·숫자·하이픈만 쓴다 (예: context-window).")
    aliases = [a.strip() for a in (aliases or []) if a.strip()]
    path = _folder(config) / f"{slug}.md"
    if path.exists():
        raise AccessDenied(f"'{slug}' 는 이미 있는 용어다. 고치려면 파일을 직접 다루는 세션에서.")
    dup = _exists(config, term, aliases)
    if dup:
        raise AccessDenied(f"'{term}' 은 이미 '{dup}' 에 있다 (별칭 포함).")

    result = check.check_text(f"{term}\n{short}\n{body}", config, ident=f"terms/{slug}")
    if result["blocking"]:
        return {"saved": False, "check": result}

    meta = {"term": term, "aliases": aliases, "short": short}
    front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, default_flow_style=None, width=1000)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + front + "---\n\n" + body.strip() + "\n", encoding="utf-8")
    return {"saved": True, "slug": slug, "path": f"src/content/terms/{slug}.md", "check": result}
