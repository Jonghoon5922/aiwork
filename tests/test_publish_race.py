"""다른 실행이 먼저 push 했을 때 publish 가 받아서 다시 올리는지."""
import subprocess
from types import SimpleNamespace

from aiwork import publish


def _git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def _clone(remote, path):
    subprocess.run(["git", "clone", "-q", str(remote), str(path)], check=True, capture_output=True)
    _git(path, "config", "user.email", "t@example.invalid")
    _git(path, "config", "user.name", "t")


def test_publish_retries_after_remote_moved(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    a, b = tmp_path / "a", tmp_path / "b"
    _clone(remote, a)
    (a / "src/content").mkdir(parents=True)
    (a / "src/content/first.md").write_text("first", encoding="utf-8")
    _git(a, "add", "."); _git(a, "commit", "-q", "-m", "init"); _git(a, "push", "-q", "origin", "HEAD:main")
    _clone(remote, b)

    # b 가 먼저 올린다
    (b / "src/content/from-b.md").write_text("b", encoding="utf-8")
    _git(b, "add", "."); _git(b, "commit", "-q", "-m", "b"); _git(b, "push", "-q", "origin", "main")

    # a 는 그 사실을 모른 채 publish
    (a / "src/content/from-a.md").write_text("a", encoding="utf-8")
    config = SimpleNamespace(site=SimpleNamespace(path=a))
    result = publish.publish(config, message="a")

    assert result["published"] is True, result
    assert (a / "src/content/from-b.md").exists()
    log = subprocess.run(["git", "-C", str(remote), "log", "--oneline", "main"], capture_output=True, text=True).stdout
    assert len(log.strip().splitlines()) == 3
