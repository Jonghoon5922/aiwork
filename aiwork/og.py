"""글별 OG 이미지 — approve 때 제목을 그려 public/og/<topic>-<slug>.png 로 둔다.

PowerShell(System.Drawing, Malgun Gothic)로 그리므로 Windows 로컬에서만 된다.
실패해도 approve 는 막지 않는다. 사이트는 파일이 있으면 쓰고 없으면 og-default.png 로 돌아간다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from . import content
from .config import Config

TOPIC_COLOR = {"coral": "#ff6b4a", "violet": "#6c5ce7", "green": "#12b886", "amber": "#f59f00", "blue": "#3b5bdb"}
KIND_LABEL = {"workbook": "워크북", "case": "사례", "analysis": "분석", "design": "설계", "build": "개발",
              "test": "테스트", "deploy": "배포", "operate": "운영", "decision": "결정", "journal": "회차", "digest": "주간"}
_SCRIPT = Path(__file__).with_name("og.ps1")


def _topic_meta(config: Config, topic: str) -> tuple[str, str]:
    for p in config.site.topics.glob("*.md"):
        if p.stem == topic:
            meta, _ = content.split_frontmatter(p.read_text(encoding="utf-8"))
            return meta.get("name") or topic, TOPIC_COLOR.get(meta.get("color", ""), "#3b5bdb")
    return topic, "#3b5bdb"


def out_path(config: Config, topic: str, slug: str) -> Path:
    return config.site.path / "public" / "og" / f"{topic}-{slug}.png"


def render(config: Config, topic: str, slug: str, title: str, kind: str | None = None) -> dict:
    name, color = _topic_meta(config, topic)
    out = out_path(config, topic, slug)
    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(_SCRIPT),
           "-Title", title, "-Out", str(out), "-Topic", name, "-Kind", KIND_LABEL.get(kind or "", ""), "-Color", color]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "note": f"OG 이미지 생성 실패: {e}"}
    if done.returncode != 0 or not out.exists():
        return {"ok": False, "note": f"OG 이미지 생성 실패: {(done.stderr or done.stdout).strip()[:300]}"}
    return {"ok": True, "path": str(out.relative_to(config.site.path))}
