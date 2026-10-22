"""Weekly AI 재료 — 등록된 피드만 읽는다.

네트워크를 쓰는 유일한 재료 도구다. 읽을 수 있는 곳은 aiwork.toml 의 [[feeds]] 뿐이고,
본문(fetch_article)은 그 피드에서 방금 받은 항목의 링크만 허용한다. 아무 URL 이나 열지 않는다.

원문을 옮기지 않는다 — 이 도구는 요약 재료를 건넬 뿐이고, 글은 출처 링크 + 두 문장 요약 + 이 사이트의 관점으로 쓴다.
"""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from . import __version__
from .config import AccessDenied, Config, Feed

UA = f"aiwork-mcp/{__version__} (+https://aihago.com)"
ARTICLE_LIMIT = 8_000
FEED_TIMEOUT = 20

# 이번 서버 실행에서 피드로 받은 링크. fetch_article 은 이 안의 URL 만 연다.
_seen_links: set[str] = set()


def _get(url: str, timeout: int = FEED_TIMEOUT) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.read()
    except urllib.error.HTTPError as e:
        raise AccessDenied(f"{url} → HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise AccessDenied(f"{url} 에 닿지 못했다: {e.reason}") from e


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return html.unescape((el.text or "").strip())


def _strip_html(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header|aside).*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<br\s*/?>|</p>|</div>|</li>|</h[1-6]>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
    raw = re.sub(r"\n\s*\n+", "\n\n", raw)
    return raw.strip()


def _parse_date(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _parse_feed(raw: bytes) -> list[dict]:
    root = ET.fromstring(raw)
    ns = {"atom": "http://www.w3.org/2005/Atom", "content": "http://purl.org/rss/1.0/modules/content/"}
    items: list[dict] = []
    # RSS 2.0
    for it in root.iter("item"):
        link = _text(it.find("link"))
        desc = _text(it.find("description")) or _text(it.find("content:encoded", ns))
        items.append({
            "title": _text(it.find("title")),
            "link": link,
            "published": _parse_date(_text(it.find("pubDate"))),
            "summary": _strip_html(desc)[:600],
        })
    # Atom
    for en in root.iter("{http://www.w3.org/2005/Atom}entry"):
        link_el = None
        for l in en.findall("atom:link", ns):
            if l.get("rel") in (None, "alternate"):
                link_el = l
                break
        link = (link_el.get("href") if link_el is not None else "") or ""
        body = _text(en.find("atom:summary", ns)) or _text(en.find("atom:content", ns))
        items.append({
            "title": _text(en.find("atom:title", ns)),
            "link": link,
            "published": _parse_date(_text(en.find("atom:updated", ns)) or _text(en.find("atom:published", ns))),
            "summary": _strip_html(body)[:600],
        })
    return items


def list_feeds(config: Config) -> list[dict]:
    return [{"name": f.name, "url": f.url, "lang": f.lang} for f in config.feeds]


def fetch_feed(config: Config, name: str, days: int = 7, limit: int = 20) -> dict:
    feed = config.feed(name)
    try:
        items = _parse_feed(_get(feed.url))
    except ET.ParseError as e:
        raise AccessDenied(f"'{name}' 피드를 읽지 못했다 (XML 아님): {e}") from e
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = [i for i in items if i["published"] is None or i["published"] >= cutoff]
    recent.sort(key=lambda i: i["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    recent = recent[:limit]
    for i in recent:
        if i["link"]:
            _seen_links.add(i["link"])
        i["published"] = i["published"].isoformat() if i["published"] else None
    return {"feed": name, "lang": feed.lang, "days": days, "count": len(recent), "items": recent}


def fetch_article(url: str, limit: int = ARTICLE_LIMIT) -> dict:
    """피드에서 받은 링크의 본문. 그 밖의 URL 은 거부한다."""
    if url not in _seen_links:
        raise AccessDenied("피드에서 받은 링크만 열 수 있다. 먼저 fetch_feed 를 호출한다.")
    raw = _get(url, timeout=25).decode("utf-8", errors="replace")
    title = ""
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw)
    if m:
        title = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
    # 본문 후보: <article> → <main> → body
    body = ""
    for tag in ("article", "main", "body"):
        mm = re.search(rf"(?is)<{tag}[^>]*>(.*?)</{tag}>", raw)
        if mm:
            body = _strip_html(mm.group(1))
            if len(body) > 400:
                break
    text = body or _strip_html(raw)
    return {"url": url, "title": title, "chars": len(text), "truncated": len(text) > limit, "text": text[:limit]}
