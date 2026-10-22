"""CLI — 설정, 등록, 현황, MCP 서버 실행.

설정 실물(`~/.aiwork/aiwork.toml`)에는 금지어와 댓글 API 키가 들어간다.
그래서 이 파일은 사이트 저장소 안에 절대 만들지 않는다.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__, collect, config as cfg, content, weekly as weekly_mod

app = typer.Typer(add_completion=False, help="aiwork — AI 활용 사이트 운영 도구", no_args_is_help=True)

# stdout 은 MCP 채널이 될 수 있다. 사람에게 하는 말은 전부 stderr 로.
err = Console(stderr=True)

DEFAULT_PATTERNS = [
    r"sk-[A-Za-z0-9]{16,}",
    r"AKIA[0-9A-Z]{16}",
    r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
]


def _s(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render(site: Path, sources: list[cfg.Source], projects: list[cfg.Project],
           forbidden: cfg.Forbidden, comments: cfg.Comments, feeds: list[cfg.Feed] | None = None) -> str:
    lines = [
        "# aiwork 설정. 이 파일은 공개 저장소에 두지 않는다 — 금지어와 댓글 API 키가 들어 있다.",
        "",
        "[site]",
        f"path = {_s(site.as_posix())}",
        "",
    ]
    for s in sources:
        lines += ["[[sources]]", f"name = {_s(s.name)}", f"path = {_s(s.path.as_posix())}", f"topic = {_s(s.topic)}", ""]
    for p in projects:
        lines += ["[[projects]]", f"name = {_s(p.name)}", f"path = {_s(p.path.as_posix())}",
                  f"public = {'true' if p.public else 'false'}"]
        if p.repo:
            lines.append(f"repo = {_s(p.repo)}")
        lines.append("")
    for f in feeds or []:
        lines += ["[[feeds]]", f"name = {_s(f.name)}", f"url = {_s(f.url)}", f"lang = {_s(f.lang)}", ""]
    lines += [
        "[forbidden]",
        "# 고객사명·내부 시스템명 등. 한 번 공개되면 되돌릴 수 없다.",
        "words = [" + ", ".join(_s(w) for w in forbidden.words) + "]",
        "# 정규식. 키·이메일 패턴 같은 것.",
        "patterns = [" + ", ".join(_s(p) for p in forbidden.patterns) + "]",
        f"detect_paths = {'true' if forbidden.detect_paths else 'false'}",
        "",
        "[comments]",
        "# 4단계 댓글 Worker. 비어 있으면 댓글 도구는 꺼진다.",
        f"api_url = {_s(comments.api_url or '')}",
        f"api_key = {_s(comments.api_key or '')}",
        "",
    ]
    return "\n".join(lines)


def _save(config: cfg.Config) -> None:
    cfg.config_path().write_text(
        render(config.site.path, config.sources, config.projects, config.forbidden, config.comments, config.feeds),
        encoding="utf-8",
    )


@app.command()
def init(site: Path = typer.Option(Path.cwd(), "--site", help="사이트 저장소 경로")) -> None:
    """`~/.aiwork/aiwork.toml` 골격을 만든다."""
    path = cfg.config_path()
    if path.exists():
        err.print(f"[yellow]이미 있다:[/yellow] {path}")
        raise typer.Exit(0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(site.resolve(), [], [], cfg.Forbidden(patterns=list(DEFAULT_PATTERNS)), cfg.Comments()),
                    encoding="utf-8")
    err.print(f"[green]설정을 만들었다:[/green] {path}")
    err.print("금지어(words) 는 직접 채운다. 이 파일은 공개 저장소에 두지 않는다.")


@app.command("add-source")
def add_source(path: Path = typer.Argument(..., help="원고 폴더"),
               topic: str = typer.Option(..., "--topic", help="이 원고가 속한 주제 slug"),
               name: str = typer.Option(None, "--name", help="이름 (기본: 폴더 이름)")) -> None:
    """원고 폴더를 등록한다."""
    config = cfg.load()
    target = path.expanduser().resolve()
    if not target.is_dir():
        err.print(f"[red]폴더가 아니다:[/red] {target}")
        raise typer.Exit(1)
    label = name or target.name
    if any(s.name == label for s in config.sources):
        err.print(f"[red]이미 등록된 이름이다:[/red] {label}")
        raise typer.Exit(1)
    config.sources.append(cfg.Source(name=label, path=target, topic=topic))
    _save(config)
    err.print(f"[green]등록했다:[/green] {label} → {target} (주제 {topic})")


@app.command("add-project")
def add_project(path: Path = typer.Argument(..., help="프로젝트 폴더 (git 저장소)"),
                name: str = typer.Option(None, "--name", help="이름 (기본: 폴더 이름)"),
                private: bool = typer.Option(False, "--private", help="재료 수집을 거부한다")) -> None:
    """연재 프로젝트를 등록한다."""
    config = cfg.load()
    target = path.expanduser().resolve()
    if not target.is_dir():
        err.print(f"[red]폴더가 아니다:[/red] {target}")
        raise typer.Exit(1)
    # 감싸는 폴더를 잘못 등록하면 그 옆의 키 파일까지 읽을 수 있게 된다.
    if not collect.is_repo(target):
        nested = [d for d in target.iterdir() if d.is_dir() and collect.is_repo(d)]
        err.print(f"[yellow]git 저장소가 아니다:[/yellow] {target}")
        for d in nested:
            err.print(f"  아래가 저장소다: {d}")
        raise typer.Exit(1)
    label = name or target.name
    if any(p.name == label for p in config.projects):
        err.print(f"[red]이미 등록된 이름이다:[/red] {label}")
        raise typer.Exit(1)
    repo = None
    try:
        repo = collect._git(target, "remote", "get-url", "origin").strip() or None
    except collect.GitError:
        pass
    config.projects.append(cfg.Project(name=label, path=target, public=not private, repo=repo))
    _save(config)
    err.print(f"[green]등록했다:[/green] {label}{' (비공개)' if private else ''} → {target}")


@app.command("add-feed")
def add_feed(url: str = typer.Argument(..., help="RSS/Atom 주소"),
             name: str = typer.Option(..., "--name", help="이름"),
             lang: str = typer.Option("en", "--lang", help="언어 (en/ko)")) -> None:
    """Weekly AI 피드를 등록한다."""
    config = cfg.load()
    if any(f.name == name for f in config.feeds):
        err.print(f"[red]이미 등록된 이름이다:[/red] {name}")
        raise typer.Exit(1)
    config.feeds.append(cfg.Feed(name=name, url=url, lang=lang))
    _save(config)
    err.print(f"[green]등록했다:[/green] {name} → {url}")


@app.command()
def status() -> None:
    """주제별 글 수·큐, 프로젝트별 밀린 커밋."""
    config = cfg.load()

    t = Table(title="주제", title_style="")
    for col in ("slug", "이름", "글", "큐 대기", "마지막 글"):
        t.add_column(col)
    for row in content.list_topics(config):
        t.add_row(row["slug"], row["name"] or "", str(row["post_count"]), str(row["queue_waiting"]),
                  row["last_post_date"] or "없음")
    err.print(t)

    p = Table(title="연재 프로젝트", title_style="")
    for col in ("이름", "공개", "마지막 글", "이후 커밋", "HEAD"):
        p.add_column(col)
    for project in config.projects:
        last = content.last_published(config, project.name)
        if not project.public:
            p.add_row(project.name, "✗", "-", "-", "-")
            continue
        n = collect.count_since(project, last.until_commit if last else None)
        p.add_row(project.name, "○", last.date.isoformat() if last and last.date else "없음",
                  str(n), collect.head(project) or "-")
    err.print(p)
    err.print("원고 폴더: " + (", ".join(f"{s.name}→{s.topic}" for s in config.sources) or "(없음)"))
    err.print("피드: " + (", ".join(f.name for f in config.feeds) or "(없음)"))


@app.command()
def serve() -> None:
    """MCP(stdio) 서버. Claude 가 이 명령을 실행한다."""
    from .server import serve as run
    config = cfg.load()
    err.print(f"[dim]aiwork MCP 시작 — 프로젝트 {len(config.projects)}개, 원고 {len(config.sources)}개[/dim]")
    run(config)


@app.command()
def weekly(
    as_json: bool = typer.Option(False, "--json", help="기계가 읽을 형태로"),
    min_commits: int = typer.Option(weekly_mod.MIN_COMMITS, "--min-commits", help="이 미만이면 프로젝트를 건너뛴다"),
    mark: bool = typer.Option(False, "--mark", help="이번 실행 시각을 기록한다 (다음 주 새 댓글 기준)"),
) -> None:
    """이번 주 할 일을 한 번에 모은다. 결과는 stdout — 스케줄로 뜬 Claude 가 읽는다."""
    import json as _json
    result = weekly_mod.gather(cfg.load(), min_commits=min_commits)
    print(_json.dumps(result, ensure_ascii=False, indent=2) if as_json else weekly_mod.render(result))
    if mark:
        weekly_mod.mark_run(result["generated_at"])
        err.print("[dim]실행 시각을 기록했다.[/dim]")


@app.command()
def version() -> None:
    err.print(f"aiwork {__version__}")
