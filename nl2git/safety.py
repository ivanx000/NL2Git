"""Safety review and approval utilities for NL2Git command execution."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm


@dataclass(frozen=True, slots=True)
class _HighRiskRule:
    name: str
    pattern: re.Pattern[str]
    reason: str


class SafetyGuard:
    """Detects risky Git commands and asks for explicit user approval."""

    HIGH_RISK_RULES: tuple[_HighRiskRule, ...] = (
        _HighRiskRule(
            name="reset-hard",
            pattern=re.compile(r"\bgit\s+reset\b.*\s--hard\b", re.IGNORECASE),
            reason="`git reset --hard` discards local changes and can permanently lose work.",
        ),
        _HighRiskRule(
            name="push-force-long",
            pattern=re.compile(r"\bgit\s+push\b.*\s--force(?:-with-lease)?\b", re.IGNORECASE),
            reason="Force push rewrites remote history and can overwrite collaborators' commits.",
        ),
        _HighRiskRule(
            name="push-force-short",
            pattern=re.compile(r"\bgit\s+push\b(?:\s+[^\s]+)*\s+-f\b", re.IGNORECASE),
            reason="`git push -f` is a force push and can rewrite shared remote history.",
        ),
        _HighRiskRule(
            name="branch-delete-force",
            pattern=re.compile(r"\bgit\s+branch\b.*\s-D\b", re.IGNORECASE),
            reason="`git branch -D` force-deletes a branch even when unmerged commits exist.",
        ),
        _HighRiskRule(
            name="clean-force-directories",
            pattern=re.compile(r"\bgit\s+clean\b.*\s-fd\b", re.IGNORECASE),
            reason="`git clean -fd` irreversibly deletes untracked files and directories.",
        ),
        _HighRiskRule(
            name="rebase",
            pattern=re.compile(r"\bgit\s+rebase\b", re.IGNORECASE),
            reason="Rebase rewrites commit history and is high-risk for beginners if used incorrectly.",
        ),
    )

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def check_risks(self, commands: List[str]) -> List[str]:
        """Return specific warning messages for any high-risk command patterns."""
        warnings: List[str] = []
        for command in commands:
            normalized = command.strip()
            if not normalized:
                continue

            for rule in self.HIGH_RISK_RULES:
                if rule.pattern.search(normalized):
                    warnings.append(
                        f"Command: {normalized}\nRisk: {rule.reason}"
                    )

        return warnings

    def get_user_approval(self, commands: List[str]) -> bool:
        """Render review output and ask for confirmation with default deny."""
        warnings = self.check_risks(commands)
        self._render_review_panel(commands, warnings)
        return Confirm.ask("Do you want to execute these commands? [y/N]", default=False)

    def _render_review_panel(self, commands: List[str], warnings: List[str]) -> None:
        command_lines = [f"- {cmd}" for cmd in commands if cmd.strip()]
        command_block = "\n".join(command_lines) if command_lines else "(no commands to run)"

        if warnings:
            warning_block = "\n\n".join(f"- {item}" for item in warnings)
            panel_body = (
                "The following commands were flagged as high-risk:\n\n"
                f"{command_block}\n\n"
                "Why they are dangerous:\n"
                f"{warning_block}"
            )
            self.console.print(
                Panel(
                    panel_body,
                    title="⚠️ DANGER",
                    border_style="red",
                )
            )
            return

        self.console.print(
            Panel(
                command_block,
                title="Review Panel",
                subtitle="All commands appear safe",
                border_style="green",
            )
        )
