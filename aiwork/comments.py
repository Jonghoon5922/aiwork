"""댓글 — Worker 관리 API 를 호출한다 (SPEC 9절).

이 모듈은 네트워크를 쓴다. 대상은 aiwork.toml [comments].api_url 하나뿐이다.
답글 본문은 check 를 거친 뒤에만 보낸다 — 댓글도 원고가 나가는 출구다.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from . import check
from .config import AccessDenied, Config


class CommentsDisabled(Exception):
    """[comments] 설정이 비어 있다."""


def _call(config: Config, method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
    if not config.comments.enabled:
        raise CommentsDisabled("aiwork.toml 의 [comments] api_url·api_key 가 비어 있다. 4단계 배포 뒤 채운다.")
    url = config.comments.api_url.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {config.comments.api_key}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise AccessDenied(f"댓글 API {e.code}: {e.read().decode('utf-8', 'replace')[:200]}") from e
    except urllib.error.URLError as e:
        raise AccessDenied(f"댓글 API 에 닿지 못했다: {e.reason}") from e


def list_comments(config: Config, since: str | None = None, post: str | None = None, include_hidden: bool = False) -> dict:
    return _call(config, "GET", "/admin/comments", params={
        "since": since, "post": post, "include_hidden": "1" if include_hidden else None,
    })


def reply(config: Config, comment_id: int, body: str) -> dict:
    result = check.check_text(body, config, ident=f"reply:{comment_id}")
    if not result["ok"]:
        raise AccessDenied(f"답글이 check 를 통과하지 못했다 ({result['blocking']}건). 보내지 않았다.")
    out = _call(config, "POST", "/admin/reply", body={"parent": comment_id, "body": body})
    out["warnings"] = result["warnings"]
    return out


def hide(config: Config, comment_id: int, reason: str = "운영자") -> dict:
    return _call(config, "POST", "/admin/hide", body={"id": comment_id, "reason": reason})


def unhide(config: Config, comment_id: int) -> dict:
    return _call(config, "POST", "/admin/unhide", body={"id": comment_id})
