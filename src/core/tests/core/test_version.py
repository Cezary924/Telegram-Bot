import subprocess

from core import version
from core.version import Version, read, tagged


def test_version_reads_as_a_tag_with_a_count():
    assert str(Version("v1.2", 100)) == "v1.2 (100)"


def test_an_unknown_version():
    assert str(Version()) == "unknown"


def test_a_build_without_a_tag_shows_only_its_count():
    assert str(Version("", 100)) == "100"


def git_without_tags(*arguments):
    if arguments[0] == "describe":
        raise subprocess.CalledProcessError(128, "git")
    return {"--abbrev-ref": "master", "HEAD": "abc123"}.get(arguments[1], "100")


def test_read_returns_what_git_says(monkeypatch):
    answers = {("rev-parse", "--abbrev-ref", "HEAD"): "master",
               ("rev-list", "--count", "master"): "100",
               ("rev-parse", "HEAD"): "abc123",
               ("describe", "--exact-match", "--tags", "abc123"): "1.2.0"}
    monkeypatch.setattr(version, "run_git", lambda *arguments: answers[arguments])
    assert read() == Version("1.2.0", 100, "abc123")


def test_a_commit_without_a_tag_of_its_own_gets_no_tag(monkeypatch):
    monkeypatch.setattr(version, "run_git", git_without_tags)
    assert read() == Version("", 100, "abc123")


def test_the_nearest_tag_is_never_borrowed(monkeypatch):
    asked = []

    def answer(*arguments):
        asked.append(arguments)
        return git_without_tags(*arguments)

    monkeypatch.setattr(version, "run_git", answer)
    read()
    assert [arguments for arguments in asked if arguments[0] == "describe"] == [
        ("describe", "--exact-match", "--tags", "abc123")]


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
    monkeypatch.setattr(version, "run_git", lambda *arguments: "2.3.0")
    assert tagged(Version("", 905, "abc123")) == Version("2.3.0", 905, "abc123")


def test_the_tag_is_looked_up_for_the_commit_that_runs(monkeypatch):
    asked = []
    monkeypatch.setattr(version, "run_git", lambda *arguments: asked.append(arguments) or "2.3.0")
    tagged(Version("", 905, "abc123"))
    assert asked == [("describe", "--exact-match", "--tags", "abc123")]


def test_a_version_without_a_commit_is_left_alone(monkeypatch):
    monkeypatch.setattr(version, "run_git", lambda *arguments: "2.3.0")
    assert tagged(Version("v1.2", 100)) == Version("v1.2", 100)


def test_parse_reads_what_str_writes():
    for written in [Version("2.3.0", 905), Version("", 905), Version()]:
        assert Version.parse(str(written)) == written


def test_parse_keeps_a_tag_with_spaces_and_brackets():
    assert Version.parse("v1 (beta) (12)") == Version("v1 (beta)", 12)
