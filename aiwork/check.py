"""마스킹 검사 — 원고가 이 PC 를 떠나기 전에 거치는 관문.

"게시 직전 검사" 가 아니라 "원고가 나가는 모든 출구" 에 둔다 (게시·수정·댓글 답글).
회사 정보 유출은 되돌릴 수 없다. 애매하면 막는 쪽으로 판단한다.

block (막는다): 금지어, 키·이메일 패턴, 등록되지 않은 절대 경로, 저자 경험담 플레이스홀더
warn  (알린다): 등록된 절대 경로, AI 스러운 문체 신호
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import Config

_BS = chr(92) * 2
_TAIL = r"[^\s" + chr(34) + chr(39) + chr(96) + r")\]]+"
_ABS_PATH = re.compile(r"(?:[A-Za-z]:[" + _BS + r"/]" + _TAIL + r"|/(?:home|Users)/" + _TAIL + r")")

# 저자 경험담 자리. 이게 남아 있으면 그 글은 못 나간다 — 지어내지 않기 위한 장치다.
PLACEHOLDER = "[저자 경험 넣을 자리"

# AI 스러운 문체 신호 (warn). 막지는 않고 Claude 가 읽고 고친다.
_HEDGES = re.compile(r"(할 수 있습니다|권합니다|것이 좋습니다|할 수 있어요|하는 것이 좋아요|수 있을 것)")
_HEDGE_LIMIT = 6

BLOCK = "block"
WARN = "warn"


@dataclass
class Finding:
    line: int
    matched: str
    rule: str
    level: str
    hint: str | None = None

    def as_dict(self) -> dict:
        return {"line": self.line, "matched": self.matched, "rule": self.rule, "level": self.level, "hint": self.hint}


def _mask(text: str, keep: int = 3) -> str:
    """걸린 문자열을 그대로 되돌려주면 그것부터가 유출이다. 앞부분만 남긴다."""
    text = text.strip()
    if len(text) <= keep:
        return text[:keep] + "…"
    return text[:keep] + "…" + f"({len(text)}자)"


def scan(text: str, config: Config) -> list[Finding]:
    findings: list[Finding] = []
    roots = [str(r).lower().replace("\\", "/") for r in config.roots()]
    hedges = 0
    tables = 0
    in_code = False

    for no, line in enumerate(text.splitlines(), start=1):
        if line.strip().startswith("```"):
            in_code = not in_code
        lowered = line.lower()

        for word in config.forbidden.words:
            if word and word.lower() in lowered:
                findings.append(Finding(no, _mask(word), "금지어", BLOCK, "설정의 words 에 등록된 낱말"))

        for pattern in config.forbidden.patterns:
            try:
                for m in re.finditer(pattern, line):
                    findings.append(Finding(no, _mask(m.group(0)), f"패턴 {pattern[:24]}", BLOCK))
            except re.error:
                continue

        if config.forbidden.detect_paths:
            for m in _ABS_PATH.finditer(line):
                found = m.group(0)
                normalized = found.lower().replace("\\", "/")
                if any(normalized.startswith(r) for r in roots):
                    findings.append(Finding(no, _mask(found, 8), "로컬 절대 경로(등록됨)", WARN,
                                            "등록된 폴더지만 공개 글에 내 PC 경로를 남길 이유는 없다"))
                else:
                    findings.append(Finding(no, _mask(found, 4), "등록되지 않은 절대 경로", BLOCK))

        if PLACEHOLDER in line:
            findings.append(Finding(no, PLACEHOLDER, "저자 경험담 비어 있음", BLOCK,
                                    "지어내지 않는다. 사용자가 채울 때까지 이 글은 못 나간다"))

        if not in_code:
            hedges += len(_HEDGES.findall(line))
            if line.lstrip().startswith("|") and line.rstrip().endswith("|") and "---" in line:
                tables += 1

    if hedges > _HEDGE_LIMIT:
        findings.append(Finding(0, f"{hedges}회", "비단정 표현 과다", WARN,
                                "'~할 수 있습니다/권합니다' 가 많다. '하세요/하지 마세요' 로 단정한다"))
    if tables >= 3:
        findings.append(Finding(0, f"표 {tables}개", "표 과다", WARN, "표는 꼭 필요한 한두 개만. 나머지는 문장으로"))
    return findings


def check_text(text: str, config: Config, ident: str = "(text)") -> dict:
    findings = scan(text, config)
    blocks = [f for f in findings if f.level == BLOCK]
    warns = [f for f in findings if f.level == WARN]
    return {
        "id": ident,
        "ok": not blocks,
        "blocking": len(blocks),
        "warnings": len(warns),
        "findings": [f.as_dict() for f in findings],
        "note": "통과. approve 할 수 있다." if not blocks else f"{len(blocks)}건이 막고 있다. 본문을 고치고 다시 check 한다.",
    }


def check_file(path: Path, config: Config) -> dict:
    return check_text(path.read_text(encoding="utf-8", errors="replace"), config, ident=path.stem)
