# NL2Git

Natural Language to Git: a terminal-native CLI that translates plain-English intent into safe, reviewable Git commands, reducing Git anxiety through guided planning, safety checks, and agentic error recovery.

## Installation

1. Ensure Python 3.12+ is installed.
2. Install the project:

```bash
pip install .
```

3. Configure your API key in a .env file at the project root:

```env
GOOGLE_API_KEY=your_api_key_here
```

4. Run the CLI:

```bash
nl2git "create a new branch called feature/auth and switch to it"
```

## How It Works

NL2Git follows a 5-phase architecture:

1. Phase 1: Context Collection
- src/nl2git/context.py builds current repository context from local Git state:
  - current branch
  - porcelain status
  - recent commits
  - ahead/behind relationship with upstream
- The context is converted into a deterministic prompt block for the LLM.

2. Phase 2: Planning Engine
- src/nl2git/engine.py sends user intent + git context to the model.
- The model returns structured JSON only:
  - commands plan (reasoning + commands)
  - or clarification request
- Output is schema-validated before use.

3. Phase 3: Safety Guard
- src/nl2git/safety.py scans commands for high-risk patterns.
- A rich review panel displays either:
  - safe green command list
  - or red danger panel with explicit risk explanations
- User approval is required with default No.

4. Phase 4: Execution Layer
- src/nl2git/executor.py runs approved Git commands using subprocess with shell=False.
- Captures stdout and stderr for each command.
- Uses stop-on-first-error behavior to prevent cascading Git failures.
- Returns structured execution results for recovery workflows.

5. Phase 5: CLI Orchestrator
- src/nl2git/main.py wires all phases into a single command: nl2git [INTENT].
- Includes:
  - --dry-run for preview mode
  - --verbose for expanded diagnostics
  - rich "Thinking..." spinner while AI plans
- If execution fails, main.py can ask for a self-healing fix and present it for another approval round.

## Self-Healing Loop

NL2Git includes an agentic recovery loop that helps users move forward when a Git command fails, rather than stopping at the first error.

1. **Error Capture**
- The execution layer intercepts failed Git commands and captures both stderr and stdout in a structured result object.
- This preserves actionable diagnostics for failures such as merge conflicts, index locks, or invalid refs.

2. **Context Refresh**
- After a failure, the orchestrator re-scans repository state using the context layer.
- The refreshed snapshot ensures follow-up recommendations are based on current branch, status, and commit context.

3. **AI Reasoning**
- The engine receives the failure details and refreshed Git context with a targeted repair prompt.
- It generates a fix-oriented command plan intended to resolve the specific failure while preserving the original user intent.

4. **User Recovery**
- The recovery plan is presented through the same safety review and explicit approval flow.
- The user can approve or reject the fix-it commands before any further execution.

This behavior elevates NL2Git from a simple command wrapper to an **Agentic Developer Tool** that can assist with real-world recovery scenarios such as merge conflicts, locked index files, and interrupted workflows.

## Safety First

Safety is a core design principle:

- Context-first prompts reduce hallucinated command plans.
- High-risk operations are flagged before execution.
- Manual approval is always required before running commands.
- Confirmation defaults to No.
- Execution stops on first command error to avoid unintended side effects.
- Non-Git commands are rejected in the executor.

## Example

```bash
nl2git "stage all changes and commit with message refactor parser"
```

You will see:
1. AI-generated plan
2. Safety review panel
3. Approval prompt
4. Command execution results

## License

See LICENSE for details.
