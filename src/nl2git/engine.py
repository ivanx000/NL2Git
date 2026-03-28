"""LLM engine for converting natural language intent into Git commands."""

from __future__ import annotations

import json
import os
from typing import Any, Literal

from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
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

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {
            "type": "clarification",
            "message": "GOOGLE_API_KEY is missing. Add it to your .env file and retry.",
        }

    genai.configure(api_key=api_key)
    model = os.getenv("NL2GIT_GEMINI_MODEL") or os.getenv("MODEL_NAME", "gemini-2.5-flash")

    # Define JSON schema for structured output
    json_schema = {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["commands", "clarification"]
            },
            "reasoning": {"type": "string"},
            "commands": {
                "type": "array",
                "items": {"type": "string"}
            },
            "message": {"type": "string"}
        },
        "required": ["type"]
    }

    user_prompt = (
        "Use the git context and user intent below. Return valid JSON only.\n\n"
        f"Git context:\n{context_string}\n\n"
        f"User intent:\n{user_intent}"
    )

    try:
        client = genai.GenerativeModel(
            model_name=model,
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.types.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=json_schema,
            ),
        )

        response = client.generate_content(user_prompt)
        raw_content = response.text or ""
        parsed_json = json.loads(raw_content)
        validated = SuggestionAdapter.validate_python(parsed_json)
        return validated.model_dump()

    except json.JSONDecodeError:
        return {
            "type": "clarification",
            "message": "I could not validate the AI response. Please rephrase your request with more Git-specific detail.",
        }
    except ValidationError:
        return {
            "type": "clarification",
            "message": "I could not validate the AI response. Please rephrase your request with more Git-specific detail.",
        }
    except google_exceptions.InvalidArgument as exc:
        return {
            "type": "clarification",
            "message": f"Gemini API error (invalid request): {exc}. Please retry with a simpler request.",
        }
    except google_exceptions.PermissionDenied as exc:
        return {
            "type": "clarification",
            "message": f"Gemini API authentication failed: {exc}. Check your GOOGLE_API_KEY.",
        }
    except Exception as exc:
        return {
            "type": "clarification",
            "message": f"Gemini API request failed: {exc}. Please retry in a moment.",
        }
