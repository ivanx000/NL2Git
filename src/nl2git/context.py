"""Git repository context collection for NL2Git prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess


@dataclass(slots=True)
class GitContext:
    """Collects local Git state and renders it as an LLM prompt block."""

    repo_path: Path | None = None
    branch: str = "unavailable"
    status_lines: list[str] = field(default_factory=list)
    modified_count: int = 0
    untracked_count: int = 0
    recent_commits: list[str] = field(default_factory=list)
    ahead_count: int | None = None
    behind_count: int | None = None
    upstream_configured: bool = True
    errors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.repo_path is None:
            self.repo_path = Path.cwd()
        else:
            self.repo_path = Path(self.repo_path)
        self.refresh()

    def refresh(self) -> None:
        """Refresh all git context fields from the repository."""
        self.errors.clear()
        self.status_lines = []
        self.recent_commits = []
        self.branch = "unavailable"
        self.modified_count = 0
        self.untracked_count = 0
        self.ahead_count = None
        self.behind_count = None
        self.upstream_configured = True

        branch_result = self._run_git(["branch", "--show-current"])
        if self._is_not_repo_error(branch_result.stderr):
            self.errors.append("fatal: not a git repository")
            self.upstream_configured = False
            return
        if branch_result.ok and branch_result.stdout.strip():
            self.branch = branch_result.stdout.strip()
        else:
            self.errors.append("branch: unavailable")

        self._load_status()
        self._load_recent_commits()
        self._load_ahead_behind()

    def to_prompt_string(self) -> str:
        """Render collected data as a clean prompt prefix for the LLM."""
        status_block = "\n".join(self.status_lines) if self.status_lines else "(clean working tree)"
        commits_block = "\n".join(self.recent_commits) if self.recent_commits else "(no commits found)"

        if self.ahead_count is None or self.behind_count is None:
            if self.upstream_configured:
                ahead_behind_line = "ahead/behind: unavailable"
            else:
                ahead_behind_line = "upstream: not configured"
        else:
            ahead_behind_line = f"ahead: {self.ahead_count}, behind: {self.behind_count}"

        errors_block = "none" if not self.errors else "; ".join(self.errors)

        return (
            "Git Context\n"
            f"branch: {self.branch}\n"
            f"modified files: {self.modified_count}\n"
            f"untracked files: {self.untracked_count}\n"
            "status --porcelain:\n"
            f"{status_block}\n"
            "recent commits (last 3):\n"
            f"{commits_block}\n"
            f"remote sync: {ahead_behind_line}\n"
            f"errors: {errors_block}"
        )

    def _load_status(self) -> None:
        result = self._run_git(["status", "--porcelain"])
        if result.ok:
            self.status_lines = [line for line in result.stdout.splitlines() if line.strip()]
            self.modified_count = sum(1 for line in self.status_lines if not line.startswith("??"))
            self.untracked_count = sum(1 for line in self.status_lines if line.startswith("??"))
            return

        self.errors.append("status: unavailable")

    def _load_recent_commits(self) -> None:
        result = self._run_git(["log", "-n", "3", "--oneline"])
        if result.ok:
            self.recent_commits = [line for line in result.stdout.splitlines() if line.strip()]
            return

        self.errors.append("log: unavailable")

    def _load_ahead_behind(self) -> None:
        result = self._run_git(["rev-list", "--left-right", "--count", "HEAD...@{u}"])
        if result.ok:
            parsed = result.stdout.strip().split()
            if len(parsed) == 2 and all(item.isdigit() for item in parsed):
                self.behind_count = int(parsed[0])
                self.ahead_count = int(parsed[1])
            else:
                self.errors.append("ahead/behind: parse failure")
            return

        if "no upstream configured" in result.stderr.lower() or "no upstream" in result.stderr.lower():
            self.upstream_configured = False
            return

        self.errors.append("ahead/behind: unavailable")

    def _run_git(self, args: list[str]) -> "_CommandResult":
        """Run a git command with shell disabled for safety."""
        completed = subprocess.run(
            ["git", *args],
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )
        return _CommandResult(
            ok=completed.returncode == 0,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    @staticmethod
    def _is_not_repo_error(stderr: str) -> bool:
        lowered = stderr.lower()
        return "not a git repository" in lowered


@dataclass(slots=True)
class _CommandResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
