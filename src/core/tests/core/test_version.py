import subprocess

from core import version
from core.version import Version, read


def test_version_reads_as_a_tag_with_a_count():
    assert str(Version("v1.2", 100)) == "v1.2 (100)"


def test_an_unknown_version():
    assert str(Version()) == "unknown (0)"


def test_read_returns_what_git_says(monkeypatch):
    answers = {("rev-parse", "--abbrev-ref", "HEAD"): "master",
               ("describe", "--abbrev=0", "--tags"): "v1.2",
               ("rev-list", "--count", "master"): "100"}
    monkeypatch.setattr(version, "run_git", lambda *arguments: answers[arguments])
    assert read() == Version("v1.2", 100)


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
