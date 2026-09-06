import subprocess
from dataclasses import dataclass

from core import paths

unknown_tag = "unknown"


@dataclass(frozen=True)
class Version:
    tag: str = ""
    commits: int = 0

    def __str__(self) -> str:
        if not self.commits:
            return unknown_tag
        return self.tag + " (" + str(self.commits) + ")" if self.tag else str(self.commits)


def run_git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=paths.root_dir,
                                   stderr=subprocess.DEVNULL).decode("utf8").strip()


def exact_tag() -> str:
    try:
        return run_git("describe", "--exact-match", "--tags")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def read() -> Version:
    try:
        branch = run_git("rev-parse", "--abbrev-ref", "HEAD")
        commits = int(run_git("rev-list", "--count", branch))
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return Version()
    return Version(exact_tag(), commits)
