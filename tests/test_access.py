"""접근 범위 — 등록된 폴더 밖은 어떤 경로 표기로도 못 읽는다."""

from pathlib import Path

import pytest

from aiwork.config import AccessDenied, Project, Source, resolve_within
from aiwork import collect, content


def test_resolve_within_blocks_parent(tmp_path: Path):
    root = tmp_path / "proj"
    root.mkdir()
    (tmp_path / "secret.txt").write_text("x")
    with pytest.raises(AccessDenied):
        resolve_within(root, "../secret.txt")


def test_read_source_reads_inside(tmp_path: Path):
    root = tmp_path / "src"
    root.mkdir()
    (root / "a.md").write_text("hello", encoding="utf-8")
    s = Source(name="s", path=root, topic="t")
    assert content.read_source(s, "a.md")["content"] == "hello"


def test_private_project_refuses(tmp_path: Path):
    p = Project(name="p", path=tmp_path, public=False)
    with pytest.raises(AccessDenied):
        collect.read_doc(p, "README.md")
