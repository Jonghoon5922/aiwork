"""마스킹 검사 — 막아야 할 것은 막고, 알려야 할 것은 알린다."""

from pathlib import Path

from aiwork import check
from aiwork.config import Comments, Config, Forbidden, Site


def _config(tmp_path: Path) -> Config:
    return Config(site=Site(path=tmp_path), sources=[], projects=[],
                  forbidden=Forbidden(words=["비밀회사"], patterns=[r"sk-[A-Za-z0-9]{16,}"]),
                  comments=Comments(), source_file=tmp_path / "x.toml")


def test_placeholder_blocks(tmp_path: Path):
    r = check.check_text("본문\n\n[저자 경험 넣을 자리: 뭐든]\n", _config(tmp_path))
    assert not r["ok"]
    assert any(f["rule"] == "저자 경험담 비어 있음" for f in r["findings"])


def test_forbidden_word_and_key_block(tmp_path: Path):
    r = check.check_text("비밀회사 얘기. 키는 sk-abcdefghijklmnopqrstuvwxyz", _config(tmp_path))
    rules = {f["rule"] for f in r["findings"]}
    assert "금지어" in rules and any(x.startswith("패턴") for x in rules)
    # 걸린 원문은 가려서 돌려준다
    assert all("비밀회사" not in f["matched"] for f in r["findings"])


def test_unregistered_path_blocks_registered_warns(tmp_path: Path):
    cfg = _config(tmp_path)
    r = check.check_text("경로 C:\\secret\\keys.txt 와 " + str(tmp_path / "a.md"), cfg)
    levels = {f["rule"]: f["level"] for f in r["findings"]}
    assert levels.get("등록되지 않은 절대 경로") == "block"
    assert levels.get("로컬 절대 경로(등록됨)") == "warn"


def test_hedges_warn_only(tmp_path: Path):
    text = "\n".join(["이렇게 할 수 있습니다."] * 8)
    r = check.check_text(text, _config(tmp_path))
    assert r["ok"] and r["warnings"] == 1


def test_https_link_is_not_a_path(tmp_path: Path):
    # Weekly AI 출처 링크의 "https://" 를 드라이브 경로("s://")로 오인하지 않는다
    r = check.check_text("출처: [OpenAI](https://openai.com/index/x) 를 보세요", _config(tmp_path))
    rules = [f["rule"] for f in r["findings"]]
    assert "등록되지 않은 절대 경로" not in rules
