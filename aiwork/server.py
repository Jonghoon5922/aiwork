"""MCP 서버 (stdio).

이 서버는 LLM 을 호출하지 않는다. 글은 사용자의 Claude 가 쓰고, 이 도구는 재료를 건네고
검사하고 게시한다. stdout 은 MCP 프로토콜 채널이라 이 모듈은 stdout 에 아무것도 출력하지 않는다.

서버 instructions 에 주제별 글 수·큐 대기 수·프로젝트별 밀린 커밋 수를 주입한다.
Claude 가 무엇이 밀려 있는지 먼저 알고 시작하게 하려는 것이다.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from . import __version__, collect, content
from .config import Config


def build_instructions(config: Config) -> str:
    lines: list[str] = []

    topics = content.list_topics(config)
    lines.append("주제: " + ", ".join(
        f"{t['name']}({t['slug']}, 글 {t['post_count']}편, 큐 대기 {t['queue_waiting']}건)" for t in topics
    ))

    rows = []
    for project in config.projects:
        if not project.public:
            rows.append(f"{project.name} (비공개 — 수집 거부)")
            continue
        last = content.last_published(config, project.name)
        n = collect.count_since(project, last.until_commit if last else None)
        when = last.date.isoformat() if last and last.date else "없음"
        rows.append(f"{project.name} (마지막 글 {when}, 이후 커밋 {n}건)")
    lines.append("연재 프로젝트: " + (", ".join(rows) if rows else "(없음)"))
    lines.append("원고 폴더: " + (", ".join(f"{s.name}→{s.topic}" for s in config.sources) or "(없음)"))
    lines.append("")
    lines.append(
        "글을 쓰기 전 재료를 모은다. 프로젝트 글은 get_changes·get_diff·read_doc, "
        "워크북·사례 글은 list_sources·read_source·list_queue 로. "
        "글 하나는 질문 하나에 답한다. question 은 사람이 검색창이나 AI 에 실제로 치는 문장으로. "
        "문체는 해요체 + 저자 목소리. 저자 경험담은 지어내지 않는다."
    )
    lines.append(
        "public = false 인 프로젝트는 재료 수집 자체가 거부된다. 우회하지 않는다."
    )
    return "\n".join(lines)


def create_server(config: Config) -> MCPServer:
    server = MCPServer(
        name="aiwork",
        title="aiwork — AI 활용 사이트 운영",
        version=__version__,
        instructions=build_instructions(config),
    )

    # ── 재료: 사이트 ───────────────────────────────────────────────────

    @server.tool(name="list_topics", description="주제 목록과 주제별 글 수·마지막 글 날짜·큐 대기 수.")
    def list_topics_tool() -> list[dict[str, Any]]:
        return content.list_topics(config)

    @server.tool(name="list_posts", description=(
        "글과 초안 목록. topic·kind(workbook/case/intro/devlog/decision/release)·project·"
        "status(draft/published/unpublished) 로 거른다."
    ))
    def list_posts_tool(topic: str | None = None, kind: str | None = None,
                        project: str | None = None, status: str | None = None) -> list[dict]:
        return content.list_posts(config, topic=topic, kind=kind, project=project, status=status)

    @server.tool(name="list_queue", description=(
        "사례 큐 — 다음에 쓸 글 후보(직군×업무). status 는 대기/작성중/게시. "
        "주간 실행은 '대기' 중 맨 위를 꺼낸다."
    ))
    def list_queue_tool(topic: str | None = None, status: str | None = None) -> list[dict]:
        return content.list_queue(config, topic=topic, status=status)

    # ── 재료: 원고 폴더 ────────────────────────────────────────────────

    @server.tool(name="list_sources", description="등록된 원고 폴더와 그 안의 문서 목록. topic 으로 거른다.")
    def list_sources_tool(topic: str | None = None) -> list[dict]:
        return content.list_sources(config, topic=topic)

    @server.tool(name="read_source", description="원고 폴더 안 문서의 원문. 등록된 폴더 밖은 거부된다.")
    def read_source_tool(source: str, path: str) -> dict:
        return content.read_source(config.source(source), path)

    # ── 재료: 프로젝트 git ────────────────────────────────────────────

    @server.tool(name="list_projects", description=(
        "연재 프로젝트 목록과 각 프로젝트의 마지막 글·이후 커밋 수. 개발 일지를 쓸 때 먼저 호출한다."
    ))
    def list_projects_tool() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for project in config.projects:
            last = content.last_published(config, project.name)
            out.append({
                "name": project.name,
                "public": project.public,
                "repo": project.repo,
                "is_git": collect.is_repo(project.path),
                "last_post_date": last.date.isoformat() if last and last.date else None,
                "last_post_commit": last.until_commit if last else None,
                "head": collect.head(project),
                "commits_since": collect.count_since(project, last.until_commit if last else None)
                if project.public else None,
            })
        return out

    @server.tool(name="get_changes", description=(
        "프로젝트의 커밋 목록과 요약. since 에는 커밋 해시나 날짜(2026-09-01). "
        "보통 마지막 글의 until_commit 을 넣어 '지난 글 이후' 를 본다."
    ))
    def get_changes_tool(project: str, since: str | None = None, limit: int = 100) -> dict:
        return collect.get_changes(config.project(project), since=since, limit=limit)

    @server.tool(name="get_diff", description=(
        "커밋 하나의 diff, 또는 특정 경로의 최근 변경 이력. commit 이나 path 중 하나는 있어야 한다."
    ))
    def get_diff_tool(project: str, commit: str | None = None, path: str | None = None) -> dict:
        return collect.get_diff(config.project(project), commit=commit, path=path)

    @server.tool(name="list_docs", description="프로젝트에서 읽을 수 있는 문서 목록(README.md, SPEC.md, docs/, .claude/).")
    def list_docs_tool(project: str) -> list[str]:
        return collect.list_docs(config.project(project))

    @server.tool(name="read_doc", description="프로젝트 안 문서의 원문. 등록된 폴더 밖은 거부된다.")
    def read_doc_tool(project: str, path: str) -> dict:
        return collect.read_doc(config.project(project), path)

    return server


def serve(config: Config) -> None:
    create_server(config).run(transport="stdio")
