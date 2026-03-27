"""LLM engine for converting natural language intent into Git commands."""

from __future__ import annotations

import json
import os
from typing import Any, Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, TypeAdapter, ValidationError


load_dotenv()


class CommandsSuggestion(BaseModel):
    type: Literal["commands"]
    reasoning: str
    commands: list[str]


class ClarificationSuggestion(BaseModel):
    type: Literal["clarification"]
    message: str


SuggestionAdapter = TypeAdapter(CommandsSuggestion | ClarificationSuggestion)


SYSTEM_PROMPT = """
You are a Senior Git Architect.
Generate safe, modern Git guidance that follows 2026 best practices.

Rules:
1. Always reason from the provided git context and user intent.
2. Prefer modern commands like `git switch` and `git restore` instead of `git checkout` when they are equivalent.
    Do not use `git checkout -b` for branch creation; use `git switch -c`.
    Do not use `git checkout <branch>` for switching; use `git switch <branch>`.
3. Never suggest destructive commands (`git reset --hard`, `git push --force`, branch deletion, history rewrites) unless the user intent is explicit and unambiguous.
4. If intent is vague, risky, or impossible from the provided context, ask one specific clarification question.
5. Return JSON only. Do not include markdown, code fences, or extra prose.

Output formats:
- If confident:
  {"type":"commands","reasoning":"Brief explanation","commands":["git cmd1","git cmd2"]}
- If clarification is needed:
  {"type":"clarification","message":"Ask the user a specific question"}
""".strip()


def suggest_commands(user_intent: str, context_string: str) -> dict[str, Any]:
    """Return structured Git command suggestions for a user intent.

    The function always returns a dictionary matching one of the supported schemas:
    - commands response with reasoning and command list
    - clarification response with one specific question
    """
    if not user_intent.strip():
        return {
            "type": "clarification",
            "message": "What Git task do you want to perform? For example: create a branch, stage files, commit, or sync with remote.",
        }

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "type": "clarification",
            "message": "OPENAI_API_KEY is missing. Add it to your .env file and retry.",
        }

    client = OpenAI(api_key=api_key)
    model = os.getenv("NL2GIT_OPENAI_MODEL") or os.getenv("MODEL_NAME", "gpt-4.1-mini")

    user_prompt = (
        "Use the git context and user intent below. Return valid JSON only.\n\n"
        f"Git context:\n{context_string}\n\n"
        f"User intent:\n{user_intent}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_content = response.choices[0].message.content or ""
        parsed_json = json.loads(raw_content)
        validated = SuggestionAdapter.validate_python(parsed_json)
        return validated.model_dump()

    except (json.JSONDecodeError, ValidationError):
        return {
            "type": "clarification",
            "message": "I could not validate the AI response. Please rephrase your request with more Git-specific detail.",
        }
    except Exception as exc:
        return {
            "type": "clarification",
            "message": f"OpenAI request failed: {exc}. Please retry in a moment.",
        }
