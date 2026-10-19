"""MCP 서버 (stdio).

이 서버는 LLM 을 호출하지 않는다. 글은 사용자의 Claude 가 쓰고, 이 도구는 재료를 건네고
검사하고 게시한다. stdout 은 MCP 프로토콜 채널이라 이 모듈은 stdout 에 아무것도 출력하지 않는다.

서버 instructions 에 주제별 글 수·큐 대기 수·프로젝트별 밀린 커밋 수를 주입한다.
Claude 가 무엇이 밀려 있는지 먼저 알고 시작하게 하려는 것이다.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from . import __version__, check as masking, collect, comments, content, drafts, publish as publishing, weekly as weekly_mod
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
    lines.append(
        "초안을 저장한 뒤 check 가 통과(block 0)하면 approve → publish 까지 사람 확인 없이 이어서 호출한다. "
        "block 이 남아 있으면 본문을 고쳐 update_post 하고 다시 check 한다. "
        "'[저자 경험 넣을 자리' 는 지어내 채우지 않는다 — 그 글은 사용자가 채울 때까지 둔다. "
        "잘못 나간 글은 unpublish → publish 로 내린다."
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
        "글과 초안 목록. topic·kind(workbook/case/intro/devlog/decision/release/journal)·project·"
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

    # ── 원고 ─────────────────────────────────────────────────────────

    @server.tool(name="save_draft", description=(
        "초안을 drafts/<topic>/ 에 저장하고 곧바로 마스킹 검사를 돌려 결과를 돌려준다. "
        "kind 는 workbook/case/intro/devlog/decision/release/journal. case 는 audience, workbook·journal 은 series·order, "
        "프로젝트 글(intro/devlog/decision/release)은 project 가 필요하고 until_commit 을 비우면 현재 HEAD 로 박는다. "
        "question 은 사람이 검색창이나 AI 에 실제로 치는 문장. materials 는 글 하단 고정 문구에 들어가는 재료 설명. "
        "큐에서 꺼낸 글이면 queue_id 를 넣는다 — approve 때 큐 상태가 '게시' 로 바뀐다. 초안은 저장소에 올라가지 않는다."
    ))
    def save_draft_tool(topic: str, kind: str, title: str, body: str, summary: str,
                        question: str | None = None, audience: str | None = None, series: str | None = None,
                        order: int | None = None, project: str | None = None, until_commit: str | None = None,
                        materials: str | None = None, faq: list[dict] | None = None, tags: list[str] | None = None,
                        queue_id: str | None = None, slug: str | None = None) -> dict:
        return drafts.save_draft(config, topic=topic, kind=kind, title=title, body=body, summary=summary,
                                 question=question, audience=audience, series=series, order=order, project=project,
                                 until_commit=until_commit, materials=materials, faq=faq, tags=tags,
                                 queue_id=queue_id, slug=slug)

    @server.tool(name="update_post", description=(
        "글이나 초안의 본문·제목·요약·질문·태그·FAQ 를 고친다. 고친 뒤 곧바로 검사한다. "
        "게시된 글은 publish 를 다시 해야 사이트에 반영된다."
    ))
    def update_post_tool(post_id: str, body: str | None = None, title: str | None = None, summary: str | None = None,
                         question: str | None = None, tags: list[str] | None = None, faq: list[dict] | None = None) -> dict:
        return drafts.update_post(config, post_id=post_id, body=body, title=title, summary=summary,
                                  question=question, tags=tags, faq=faq)

    # ── 관문 ─────────────────────────────────────────────────────────

    @server.tool(name="check", description=(
        "마스킹 검사. draft_id(topic/slug) 또는 text 중 하나를 준다. "
        "block: 금지어, 키·이메일 패턴, 등록되지 않은 절대 경로, '[저자 경험 넣을 자리' 플레이스홀더. "
        "warn: AI 스러운 문체(비단정 표현 과다, 표 과다). block 이 하나라도 있으면 approve 할 수 없다. "
        "걸린 원문은 그대로 돌려주지 않는다."
    ))
    def check_tool(draft_id: str | None = None, text: str | None = None) -> dict:
        if text is not None:
            return masking.check_text(text, config)
        if not draft_id:
            raise ValueError("draft_id 나 text 중 하나는 필요하다.")
        path, _ = drafts._find(config, draft_id)
        result = masking.check_file(path, config)
        result["id"] = draft_id
        return result

    @server.tool(name="approve", description=(
        "check 통과를 확인하고 초안을 posts/ 로 옮긴다. 큐에 연결된 글이면 큐 상태를 '게시' 로 바꾼다. "
        "check 통과 시 사람 확인 없이 호출해도 된다 (자동 게시 정책). 이어서 publish 를 호출한다."
    ))
    def approve_tool(draft_id: str) -> dict:
        return drafts.approve(config, draft_id)

    # ── 운영 ─────────────────────────────────────────────────────────

    @server.tool(name="publish", description=(
        "src/content 의 변경(승인된 글, 큐 상태, 내린 글)을 커밋하고 push 한다. push 가 곧 배포다. "
        "check 를 통과한 글만 posts/ 에 있으므로 사람 확인 없이 호출해도 된다."
    ))
    def publish_tool(message: str | None = None) -> dict:
        return publishing.publish(config, message=message)

    @server.tool(name="unpublish", description="게시된 글을 사이트에서 내린다(draft: true). 이어서 publish 를 호출해야 실제로 내려간다. 비상구다.")
    def unpublish_tool(post_id: str) -> dict:
        return drafts.unpublish(config, post_id)

    @server.tool(name="deploy_status", description="GitHub Actions 최근 빌드·배포 상태. publish 뒤에 확인한다.")
    def deploy_status_tool() -> dict:
        return publishing.deploy_status(config)

    @server.tool(name="site_state", description="사이트 저장소 상태 — 브랜치, 커밋 안 된 콘텐츠 변경, push 안 된 커밋 수.")
    def site_state_tool() -> dict:
        return publishing.state(config)

    # ── 주간 (5단계) ─────────────────────────────────────────────────

    @server.tool(name="weekly", description=(
        "이번 주 할 일을 한 번에 모은다: 변경 있는 프로젝트(개발 일지 후보), 사례 큐 다음 1건, "
        "워크북 플레이스홀더 수와 게시된 편, 지난 실행 이후 새 댓글. 주간 실행의 첫 호출."
    ))
    def weekly_tool(min_commits: int = weekly_mod.MIN_COMMITS) -> dict:
        return weekly_mod.gather(config, min_commits=min_commits)

    @server.tool(name="mark_weekly_run", description="이번 주간 실행이 끝났음을 기록한다. 다음 주 '새 댓글' 기준 시각이 된다. 주간 실행의 마지막 호출.")
    def mark_weekly_run_tool() -> dict:
        weekly_mod.mark_run()
        return {"ok": True, "last_run": weekly_mod.load_state().get("last_run")}

    # ── 댓글 (4단계) ─────────────────────────────────────────────────

    @server.tool(name="list_comments", description=(
        "독자 댓글 목록. since(ISO 날짜) 이후, post(topic/slug) 로 거른다. include_hidden 이면 자동 숨김된 것도. "
        "운영자 답글은 제외된다. 좋은 질문은 다음 글 후보(큐)로 넣는다."
    ))
    def list_comments_tool(since: str | None = None, post: str | None = None, include_hidden: bool = False) -> dict:
        return comments.list_comments(config, since=since, post=post, include_hidden=include_hidden)

    @server.tool(name="reply_comment", description=(
        "댓글에 운영자(AI) 답글을 단다. 본문은 check 를 통과해야 보내진다. 해요체로, 짧게."
    ))
    def reply_comment_tool(comment_id: int, body: str) -> dict:
        return comments.reply(config, comment_id, body)

    @server.tool(name="hide_comment", description="댓글을 숨긴다(스팸·금지어). 지우지는 않는다.")
    def hide_comment_tool(comment_id: int, reason: str = "운영자") -> dict:
        return comments.hide(config, comment_id, reason)

    @server.tool(name="unhide_comment", description="자동 숨김된 댓글을 다시 보이게 한다.")
    def unhide_comment_tool(comment_id: int) -> dict:
        return comments.unhide(config, comment_id)

    return server


def serve(config: Config) -> None:
    create_server(config).run(transport="stdio")
