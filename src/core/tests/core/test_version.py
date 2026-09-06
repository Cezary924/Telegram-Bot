import subprocess

from core import version
from core.version import Version, read


def test_version_reads_as_a_tag_with_a_count():
    assert str(Version("v1.2", 100)) == "v1.2 (100)"


def test_an_unknown_version():
    assert str(Version()) == "unknown"


def test_a_build_without_a_tag_shows_only_its_count():
    assert str(Version("", 100)) == "100"


def test_read_returns_what_git_says(monkeypatch):
    answers = {("rev-parse", "--abbrev-ref", "HEAD"): "master",
               ("describe", "--exact-match", "--tags"): "1.2.0",
               ("rev-list", "--count", "master"): "100"}
    monkeypatch.setattr(version, "run_git", lambda *arguments: answers[arguments])
    assert read() == Version("1.2.0", 100)


def test_a_commit_without_a_tag_of_its_own_gets_no_tag(monkeypatch):
    def answer(*arguments):
        if arguments[0] == "describe":
            raise subprocess.CalledProcessError(128, "git")
        return "master" if arguments[0] == "rev-parse" else "100"

    monkeypatch.setattr(version, "run_git", answer)
    assert read() == Version("", 100)


def test_the_nearest_tag_is_never_borrowed(monkeypatch):
    asked = []

    def answer(*arguments):
        asked.append(arguments)
        if arguments[0] == "describe":
            raise subprocess.CalledProcessError(128, "git")
        return "master" if arguments[0] == "rev-parse" else "100"

    monkeypatch.setattr(version, "run_git", answer)
    read()
    assert ("describe", "--abbrev=0", "--tags") not in asked


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
