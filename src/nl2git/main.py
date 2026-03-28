"""CLI orchestrator for NL2Git: natural language to Git commands."""

from __future__ import annotations

import os
import subprocess

import typer
from rich.console import Console
from rich.panel import Panel

from nl2git.context import GitContext
from nl2git.engine import suggest_commands
from nl2git.executor import run_git_commands
from nl2git.safety import SafetyGuard


app = typer.Typer(help="Convert natural language intent into safe Git commands.")
console = Console()


def _is_git_repository() -> bool:
    """Return True if current directory is inside a Git work tree."""
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def _show_api_key_setup_panel() -> None:
    """Render setup guidance when GOOGLE_API_KEY is missing."""
    content = (
        "GOOGLE_API_KEY is not configured.\n\n"
        "Set it in a .env file in your project root:\n"
        "GOOGLE_API_KEY=your_api_key_here\n\n"
        "Then rerun your command."
    )
    console.print(
        Panel(
            content,
            title="API Key Required",
            border_style="yellow",
        )
    )


@app.command()
def main(
    intent: str = typer.Argument(..., help="Natural language description of what you want to do."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would run without executing."),
    verbose: bool = typer.Option(False, "--verbose", help="Show AI reasoning for each step."),
) -> None:
    """Main entry point: interpret intent, generate commands, and execute with approval."""
    if not os.getenv("GOOGLE_API_KEY"):
        _show_api_key_setup_panel()
        raise typer.Exit(code=1)

    if not _is_git_repository():
        console.print(
            Panel(
                "This folder is not a Git repository.\n\n"
                "Run this command in a repository, or initialize one with:\n"
                "git init",
                title="Git Repository Required",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=1)

    console.print("[bold cyan]NL2Git[/bold cyan]: Translating natural language to Git commands.\n")

    with console.status("[bold yellow]Collecting Git context...[/bold yellow]"):
        context = GitContext()
        context_string = context.to_prompt_string()

    if verbose:
        console.print("\n[dim]Git Context:[/dim]")
        console.print(context_string)
        console.print()

    _run_suggestion_loop(intent, context_string, dry_run, verbose, original_intent=intent)


def _run_suggestion_loop(
    user_intent: str,
    context_string: str,
    dry_run: bool,
    verbose: bool,
    retry_count: int = 0,
    original_intent: str | None = None,
) -> None:
    """Core loop: suggest, approve, execute, and optionally self-heal on failure."""
    max_retries = 2
    if original_intent is None:
        original_intent = user_intent

    with console.status("[bold yellow]Thinking...[/bold yellow]"):
        suggestion = suggest_commands(user_intent, context_string)

    if verbose:
        console.print("\n[dim]AI Response:[/dim]")
        console.print(suggestion)
        console.print()

    if suggestion["type"] == "clarification":
        console.print(f"\n[yellow]Clarification needed:[/yellow] {suggestion['message']}")
        return

    if suggestion["type"] != "commands":
        console.print("[red]Error: Unexpected response type from engine.[/red]")
        return

    reasoning = suggestion.get("reasoning", "")
    commands = suggestion.get("commands", [])

    if not commands:
        console.print("[yellow]No commands to execute.[/yellow]")
        return

    if reasoning and verbose:
        console.print(f"\n[dim]Reasoning:[/dim] {reasoning}\n")

    safety_guard = SafetyGuard(console=console)
    if not safety_guard.get_user_approval(commands):
        console.print("[yellow]Execution cancelled by user.[/yellow]")
        return

    if dry_run:
        console.print("\n[cyan][Dry Run Mode][/cyan] Commands would execute as follows:")

    results = run_git_commands(commands, dry_run=dry_run, stop_on_first_error=True)

    if not results:
        console.print("[yellow]No results to process.[/yellow]")
        return

    first_failure = next((r for r in results if not r.success), None)
    if first_failure:
        console.print(
            f"\n[red]Execution failed:[/red] {first_failure.command}\n"
            f"Error: {first_failure.error_message}"
        )

        if retry_count < max_retries:
            console.print(
                f"\n[cyan]Attempting self-healing...[/cyan] (retry {retry_count + 1}/{max_retries})"
            )

            self_heal_prompt = (
                "The previous command failed with this error:\n\n"
                f"Command: {first_failure.command}\n"
                f"Error: {first_failure.error_message}\n\n"
                f"Output:\n{first_failure.output}\n\n"
                f"How do we fix this and complete the original intent: '{original_intent}'?"
            )

            with console.status("[bold yellow]Refreshing Git context...[/bold yellow]"):
                fresh_context = GitContext()
                fresh_context_string = fresh_context.to_prompt_string()

            console.print()
            _run_suggestion_loop(
                self_heal_prompt,
                fresh_context_string,
                dry_run,
                verbose,
                retry_count + 1,
                original_intent=original_intent,
            )
        else:
            console.print(f"\n[red]Max retries ({max_retries}) reached. Stopping.[/red]")

        return

    console.print("\n[green]✅ All commands executed successfully![/green]")

    if verbose:
        console.print("\n[dim]Execution Results:[/dim]")
        for result in results:
            status = "✅" if result.success else "❌"
            console.print(f"{status} {result.command}")
            if result.output:
                preview = result.output[:100]
                suffix = "..." if len(result.output) > 100 else ""
                console.print(f"   Output: {preview}{suffix}")


if __name__ == "__main__":
    app()
