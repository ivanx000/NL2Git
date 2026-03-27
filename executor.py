"""Execution layer for running approved Git commands safely."""

from __future__ import annotations

from dataclasses import dataclass
import shlex
import subprocess
from typing import List

from rich.console import Console


@dataclass(slots=True)
class ExecutionResult:
    """Structured result for each executed command."""

    success: bool
    command: str
    output: str
    error_message: str


def run_git_commands(commands: List[str], dry_run: bool = False) -> List[ExecutionResult]:
    """Run approved Git commands and return structured per-command results.

    Commands are executed sequentially. Failures are captured and returned so the
    caller can use them for feedback or self-healing suggestions.
    """
    console = Console()
    results: List[ExecutionResult] = []

    for raw_command in commands:
        command = raw_command.strip()
        if not command:
            console.print("[yellow]Skipping empty command.[/yellow]")
            results.append(
                ExecutionResult(
                    success=False,
                    command=raw_command,
                    output="",
                    error_message="Empty command string.",
                )
            )
            continue

        if dry_run:
            console.print(f"[cyan]DRY RUN[/cyan] Running: {command}... [green]✅ Skipped[/green]")
            results.append(
                ExecutionResult(
                    success=True,
                    command=command,
                    output="Dry run enabled; command was not executed.",
                    error_message="",
                )
            )
            continue

        try:
            argv = shlex.split(command)
        except ValueError as exc:
            console.print(f"[red]Running: {command}... ❌ Failed[/red]")
            results.append(
                ExecutionResult(
                    success=False,
                    command=command,
                    output="",
                    error_message=f"Command parse failed: {exc}",
                )
            )
            continue

        if not argv or argv[0] != "git":
            console.print(f"[red]Running: {command}... ❌ Failed[/red]")
            results.append(
                ExecutionResult(
                    success=False,
                    command=command,
                    output="",
                    error_message="Only git commands are allowed in executor.",
                )
            )
            continue

        try:
            with console.status(f"Running: {command}..."):
                completed = subprocess.run(
                    argv,
                    shell=False,
                    check=True,
                    capture_output=True,
                    text=True,
                )

            output_text = _combine_output(completed.stdout, completed.stderr)
            console.print(f"[green]Running: {command}... ✅ Success[/green]")
            results.append(
                ExecutionResult(
                    success=True,
                    command=command,
                    output=output_text,
                    error_message="",
                )
            )

        except subprocess.CalledProcessError as exc:
            output_text = _combine_output(exc.stdout, exc.stderr)
            console.print(f"[red]Running: {command}... ❌ Failed[/red]")
            results.append(
                ExecutionResult(
                    success=False,
                    command=command,
                    output=output_text,
                    error_message=str(exc),
                )
            )

    return results


def _combine_output(stdout: str | None, stderr: str | None) -> str:
    """Combine stdout/stderr into one readable output block."""
    stdout = (stdout or "").strip()
    stderr = (stderr or "").strip()

    if stdout and stderr:
        return f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
    if stdout:
        return stdout
    if stderr:
        return stderr
    return ""
