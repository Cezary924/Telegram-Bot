import re
import subprocess
from dataclasses import dataclass, replace

from core import paths

unknown_tag = "unknown"


@dataclass(frozen=True)
class Version:
    tag: str = ""
    commits: int = 0
    commit: str = ""

    def __str__(self) -> str:
        if not self.commits:
            return unknown_tag
        return self.tag + " (" + str(self.commits) + ")" if self.tag else str(self.commits)

    @classmethod
    def parse(cls, text: str) -> "Version":
        found = re.fullmatch(r"(?:(.+) \()?(\d+)\)?", text)
        return cls(found.group(1) or "", int(found.group(2))) if found else cls()


def run_git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=paths.root_dir,
                                   stderr=subprocess.DEVNULL).decode("utf8").strip()


def exact_tag(commit: str) -> str:
    try:
        return run_git("describe", "--exact-match", "--tags", commit)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def read() -> Version:
    try:
        branch = run_git("rev-parse", "--abbrev-ref", "HEAD")
        commits = int(run_git("rev-list", "--count", branch))
        commit = run_git("rev-parse", "HEAD")
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return Version()
    return Version(exact_tag(commit), commits, commit)


def tagged(version: Version) -> Version:
    return replace(version, tag=exact_tag(version.commit)) if version.commit else version
