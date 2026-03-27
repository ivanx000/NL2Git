# NL2Git

Natural Language to Git: a terminal-native CLI that translates plain-English intent into safe, reviewable Git commands.

## Installation

1. Ensure Python 3.12+ is installed.
2. Install the project:

```bash
pip install .
```

3. Configure your API key in a .env file at the project root:

```env
OPENAI_API_KEY=your_api_key_here
```

4. Run the CLI:

```bash
git-ai "create a new branch called feature/auth and switch to it"
```

## How It Works

NL2Git follows a 5-phase architecture:

1. Phase 1: Context Collection
- context.py builds current repository context from local Git state:
  - current branch
  - porcelain status
  - recent commits
  - ahead/behind relationship with upstream
- The context is converted into a deterministic prompt block for the LLM.

2. Phase 2: Planning Engine
- engine.py sends user intent + git context to the model.
- The model returns structured JSON only:
  - commands plan (reasoning + commands)
  - or clarification request
- Output is schema-validated before use.

3. Phase 3: Safety Guard
- safety.py scans commands for high-risk patterns.
- A rich review panel displays either:
  - safe green command list
  - or red danger panel with explicit risk explanations
- User approval is required with default No.

4. Phase 4: Execution Layer
- executor.py runs approved Git commands using subprocess with shell=False.
- Captures stdout and stderr for each command.
- Uses stop-on-first-error behavior to prevent cascading Git failures.
- Returns structured execution results for recovery workflows.

5. Phase 5: CLI Orchestrator
- main.py wires all phases into a single command: git-ai [INTENT].
- Includes:
  - --dry-run for preview mode
  - --verbose for expanded diagnostics
  - rich "Thinking..." spinner while AI plans
- If execution fails, main.py can ask for a self-healing fix and present it for another approval round.

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
git-ai "stage all changes and commit with message refactor parser"
```

You will see:
1. AI-generated plan
2. Safety review panel
3. Approval prompt
4. Command execution results

## License

See LICENSE for details.
