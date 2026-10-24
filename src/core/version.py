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
    ahead: int = 0

    def __str__(self) -> str:
        if not self.commits:
            return unknown_tag
        if not self.tag:
            return str(self.commits)
        return self.tag + ("+" + str(self.ahead) if self.ahead else "") + " (" + str(self.commits) + ")"

    @classmethod
    def parse(cls, text: str) -> "Version":
        found = re.fullmatch(r"(?:(.+?)(?:\+(\d+))? \()?(\d+)\)?", text)
        if not found:
            return cls()
        return cls(found.group(1) or "", int(found.group(3)), ahead=int(found.group(2) or 0))


def run_git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=paths.root_dir,
                                   stderr=subprocess.DEVNULL).decode("utf8").strip()


def nearest_tag(commit: str) -> tuple[str, int]:
    try:
        tag, ahead, _ = run_git("describe", "--tags", "--long", commit).rsplit("-", 2)
        return tag, int(ahead)
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return "", 0


def read() -> Version:
    try:
        branch = run_git("rev-parse", "--abbrev-ref", "HEAD")
        commits = int(run_git("rev-list", "--count", branch))
        commit = run_git("rev-parse", "HEAD")
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return Version()
    return tagged(Version(commits=commits, commit=commit))


def tagged(version: Version) -> Version:
    if not version.commit:
        return version
    tag, ahead = nearest_tag(version.commit)
    return replace(version, tag=tag, ahead=ahead)
