import subprocess
from dataclasses import dataclass

from core import paths

unknown_tag = "unknown"


@dataclass(frozen=True)
class Version:
    tag: str = unknown_tag
    commits: int = 0

    def __str__(self) -> str:
        return self.tag + " (" + str(self.commits) + ")"


def run_git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=paths.root_dir,
                                   stderr=subprocess.DEVNULL).decode("utf8").strip()


def read() -> Version:
    try:
        branch = run_git("rev-parse", "--abbrev-ref", "HEAD")
        return Version(run_git("describe", "--abbrev=0", "--tags"),
                       int(run_git("rev-list", "--count", branch)))
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return Version()
