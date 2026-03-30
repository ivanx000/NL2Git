# Output settings
Output assets/intelligent-intent.gif
Set FontSize 22
Set Width 1200
Set Height 750
Set Padding 40
Set Theme "Catppuccin Macchiato"
Set TypingSpeed 65ms

# --- Scene 1: Natural Language Intent ---
# The user asks githelp to handle their changes.
# We use the full path to the binary to ensure it runs in the demo environment.
Type "./.venv/bin/githelp -m 'Help me add my new code changes to GitHub' --verbose --dry-run"
Sleep 500ms
Enter

# Allow time for context collection + AI thinking.
Sleep 6s

# --- Scene 2: The Interactive Step-by-Step Flow ---
# In dry-run mode, the tool prints step-by-step commands without prompting for confirmation.
Sleep 8s

# Show the task completion message.
Sleep 4s

# End on the tool output (no manually typed fake success line).
Sleep 2s
