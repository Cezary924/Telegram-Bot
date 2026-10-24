import subprocess

from core import version
from core.version import Version, read, tagged


def test_version_reads_as_a_tag_with_a_count():
    assert str(Version("v1.2", 100)) == "v1.2 (100)"


def test_an_unknown_version():
    assert str(Version()) == "unknown"


def test_a_build_without_a_tag_shows_only_its_count():
    assert str(Version("", 100)) == "100"


def git_with(description: str):
    def answer(*arguments):
        if arguments[0] == "describe":
            if not description:
                raise subprocess.CalledProcessError(128, "git")
            return description
        return {"--abbrev-ref": "master", "HEAD": "abc123"}.get(arguments[1], "100")

    return answer


def test_read_returns_what_git_says(monkeypatch):
    answers = {("rev-parse", "--abbrev-ref", "HEAD"): "master",
               ("rev-list", "--count", "master"): "100",
               ("rev-parse", "HEAD"): "abc123",
               ("describe", "--tags", "--long", "abc123"): "1.2.0-0-gabc123"}
    monkeypatch.setattr(version, "run_git", lambda *arguments: answers[arguments])
    assert read() == Version("1.2.0", 100, "abc123")


def test_a_build_past_a_tag_says_how_far(monkeypatch):
    monkeypatch.setattr(version, "run_git", git_with("2.3.1-2-g0f07fd3"))
    assert read() == Version("2.3.1", 100, "abc123", ahead=2)
    assert str(read()) == "2.3.1+2 (100)"


def test_a_tag_with_dashes_is_kept_whole(monkeypatch):
    monkeypatch.setattr(version, "run_git", git_with("v1-beta-3-gabc123"))
    assert read() == Version("v1-beta", 100, "abc123", ahead=3)


def test_a_repository_without_tags_gives_only_the_count(monkeypatch):
    monkeypatch.setattr(version, "run_git", git_with(""))
    assert read() == Version("", 100, "abc123")
    assert str(read()) == "100"


def test_read_survives_a_repository_without_git(monkeypatch):
    def refuse(*_arguments):
        raise subprocess.CalledProcessError(128, "git")

    monkeypatch.setattr(version, "run_git", refuse)
    assert read() == Version()


def test_read_survives_git_being_absent(monkeypatch):
    def refuse(*_arguments):
        raise FileNotFoundError("git")

    monkeypatch.setattr(version, "run_git", refuse)
    assert read() == Version()


def test_read_survives_a_nonsense_count(monkeypatch):
    monkeypatch.setattr(version, "run_git", lambda *arguments: "not a number")
    assert read() == Version()


def test_a_tag_given_after_the_start_is_found(monkeypatch):
    monkeypatch.setattr(version, "run_git", lambda *arguments: "2.3.0-0-gabc123")
    assert tagged(Version("", 905, "abc123")) == Version("2.3.0", 905, "abc123")


def test_the_tag_is_looked_up_for_the_commit_that_runs(monkeypatch):
    asked = []
    monkeypatch.setattr(version, "run_git", lambda *arguments: asked.append(arguments) or "2.3.0-0-gabc123")
    tagged(Version("", 905, "abc123"))
    assert asked == [("describe", "--tags", "--long", "abc123")]


def test_a_version_without_a_commit_is_left_alone(monkeypatch):
    monkeypatch.setattr(version, "run_git", lambda *arguments: "2.3.0-0-gabc123")
    assert tagged(Version("v1.2", 100)) == Version("v1.2", 100)


def test_parse_reads_what_str_writes():
    for written in [Version("2.3.1", 909, ahead=2), Version("2.3.0", 905), Version("", 905), Version()]:
        assert Version.parse(str(written)) == written


def test_parse_keeps_a_tag_with_spaces_and_brackets():
    assert Version.parse("v1 (beta) (12)") == Version("v1 (beta)", 12)
