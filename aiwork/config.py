"""설정과 접근 범위.

이 도구가 읽을 수 있는 곳은 aiwork.toml 에 등록된 곳뿐이다.
    [site]        사이트 저장소 (글·주제·큐가 산다)
    [[sources]]   원고 폴더 (워크북 같은 재료)
    [[projects]]  연재할 프로젝트의 git 저장소
그 밖의 경로 요청은 전부 거부한다.

설정 실물은 ~/.aiwork/aiwork.toml 에만 둔다. 금지어 목록과 댓글 API 키가 들어 있어서
공개 저장소에 절대 들어가면 안 된다.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIRNAME = ".aiwork"
CONFIG_FILENAME = "aiwork.toml"


class ConfigError(Exception):
    """설정이 없거나 잘못됐다."""


class AccessDenied(Exception):
    """등록되지 않은 경로, 또는 비공개 프로젝트에 대한 접근."""


@dataclass
class Site:
    path: Path
    posts_dir: str = "src/content/posts"
    drafts_dir: str = "drafts"
    topics_dir: str = "src/content/topics"
    projects_dir: str = "src/content/projects"
    queue_dir: str = "src/content/queue"

    @property
    def posts(self) -> Path:
        return self.path / self.posts_dir

    @property
    def drafts(self) -> Path:
        return self.path / self.drafts_dir

    @property
    def topics(self) -> Path:
        return self.path / self.topics_dir

    @property
    def project_cards(self) -> Path:
        return self.path / self.projects_dir

    @property
    def queue(self) -> Path:
        return self.path / self.queue_dir


@dataclass
class Source:
    """원고 폴더. 어느 주제의 재료인지 알고 있다."""

    name: str
    path: Path
    topic: str


@dataclass
class Project:
    """연재할 프로젝트. git 저장소여야 한다."""

    name: str
    path: Path
    public: bool = True
    repo: str | None = None

    def require_public(self) -> None:
        """비공개 프로젝트는 재료 수집 자체를 거부한다."""
        if not self.public:
            raise AccessDenied(
                f"'{self.name}' 은 public = false 로 등록돼 있다. 재료 수집을 거부한다."
            )


@dataclass
class Feed:
    """Weekly AI 재료 피드. 이 목록 밖은 읽지 않는다."""

    name: str
    url: str
    lang: str = "en"


@dataclass
class Forbidden:
    """마스킹 검사 규칙. 실물 목록은 설정 파일에만 있다."""

    words: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    detect_paths: bool = True


@dataclass
class Comments:
    """댓글 Worker 연결 정보 (4단계). 비어 있으면 댓글 도구는 꺼진다."""

    api_url: str | None = None
    api_key: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_url and self.api_key)


@dataclass
class Config:
    site: Site
    sources: list[Source]
    projects: list[Project]
    forbidden: Forbidden
    comments: Comments
    source_file: Path
    feeds: list[Feed] = field(default_factory=list)

    def feed(self, name: str) -> Feed:
        for f in self.feeds:
            if f.name == name:
                return f
        known = ", ".join(f.name for f in self.feeds) or "(없음)"
        raise AccessDenied(f"'{name}' 은 등록되지 않은 피드다. 등록된 것: {known}")

    def project(self, name: str) -> Project:
        for p in self.projects:
            if p.name == name:
                return p
        known = ", ".join(p.name for p in self.projects) or "(없음)"
        raise AccessDenied(f"'{name}' 은 등록되지 않은 프로젝트다. 등록된 것: {known}")

    def source(self, name: str) -> Source:
        for s in self.sources:
            if s.name == name:
                return s
        known = ", ".join(s.name for s in self.sources) or "(없음)"
        raise AccessDenied(f"'{name}' 은 등록되지 않은 원고 폴더다. 등록된 것: {known}")

    def roots(self) -> list[Path]:
        """읽기가 허용된 뿌리 전부. 마스킹 검사의 경로 탐지가 이걸 기준으로 삼는다."""
        return [p.path for p in self.projects] + [s.path for s in self.sources] + [self.site.path]


def config_dir() -> Path:
    """설정 폴더. AIWORK_HOME 으로 덮어쓸 수 있다 (테스트용)."""
    override = os.environ.get("AIWORK_HOME")
    if override:
        return Path(override)
    return Path.home() / CONFIG_DIRNAME


def config_path() -> Path:
    return config_dir() / CONFIG_FILENAME


def _path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def load(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        raise ConfigError(f"설정이 없다: {path}\n`aiwork init` 으로 만든다.")

    with path.open("rb") as f:
        raw = tomllib.load(f)

    site_raw = raw.get("site") or {}
    if not site_raw.get("path"):
        raise ConfigError("[site] path 가 필요하다.")
    site = Site(
        path=_path(site_raw["path"]),
        posts_dir=site_raw.get("posts_dir", Site.posts_dir),
        drafts_dir=site_raw.get("drafts_dir", Site.drafts_dir),
        topics_dir=site_raw.get("topics_dir", Site.topics_dir),
        projects_dir=site_raw.get("projects_dir", Site.projects_dir),
        queue_dir=site_raw.get("queue_dir", Site.queue_dir),
    )

    sources: list[Source] = []
    for item in raw.get("sources", []):
        if not item.get("name") or not item.get("path") or not item.get("topic"):
            raise ConfigError(f"[[sources]] 에 name·path·topic 이 필요하다: {item!r}")
        sources.append(Source(name=item["name"], path=_path(item["path"]), topic=item["topic"]))

    projects: list[Project] = []
    for item in raw.get("projects", []):
        if not item.get("name") or not item.get("path"):
            raise ConfigError(f"[[projects]] 에 name·path 가 필요하다: {item!r}")
        projects.append(
            Project(
                name=item["name"],
                path=_path(item["path"]),
                public=bool(item.get("public", True)),
                repo=item.get("repo"),
            )
        )

    f_raw = raw.get("forbidden") or {}
    forbidden = Forbidden(
        words=list(f_raw.get("words", [])),
        patterns=list(f_raw.get("patterns", [])),
        detect_paths=bool(f_raw.get("detect_paths", True)),
    )

    c_raw = raw.get("comments") or {}
    comments = Comments(api_url=c_raw.get("api_url"), api_key=c_raw.get("api_key"))

    feeds: list[Feed] = []
    for item in raw.get("feeds", []):
        if not item.get("name") or not item.get("url"):
            raise ConfigError(f"[[feeds]] 에 name·url 이 필요하다: {item!r}")
        feeds.append(Feed(name=item["name"], url=item["url"], lang=item.get("lang", "en")))

    return Config(
        site=site, sources=sources, projects=projects,
        forbidden=forbidden, comments=comments, source_file=path, feeds=feeds,
    )


def resolve_within(root: Path, relative: str) -> Path:
    """root 안의 경로로만 풀어준다. `..` 이나 심볼릭 링크로 빠져나가는 경로는 실제 경로로 확인해서 막는다."""
    root = root.resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise AccessDenied(f"등록된 폴더 밖이다: {relative}")
    return candidate
