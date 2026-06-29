# Agent Teams — Reference Guide

Source: https://code.claude.com/docs/en/agent-teams (Claude Code v2.1.178+)

Experimental feature. Enabled in this project via `.claude/settings.local.json`:

```json
{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
```

## What it is

Multiple independent Claude Code sessions ("teammates") coordinating on a shared task list, with one session acting as **lead**. Teammates each have their own context window and message each other directly — unlike subagents, which only report back to the caller.

| | Subagents | Agent teams |
|---|---|---|
| Context | Own window, results return to caller | Own window, fully independent |
| Communication | Report to main agent only | Teammates message each other directly |
| Coordination | Main agent manages all work | Shared task list, self-coordination |
| Token cost | Lower (summarized back) | Higher (each teammate is a full instance) |

**Use agent teams when:** teammates need to discuss, challenge each other's findings, or self-coordinate.
**Use subagents when:** you just need a focused result back, no inter-agent discussion needed.

## When to actually use this

Good fits:
- **Research/review**: independent angles on the same artifact (e.g. security/performance/test-coverage review of one PR)
- **New, independent modules/features**: each teammate owns a separate piece
- **Debugging with competing hypotheses**: parallel theories that try to disprove each other (avoids anchoring bias from sequential investigation)
- **Cross-layer work**: frontend/backend/tests owned by different teammates

Bad fits — coordination overhead and token cost aren't worth it:
- Sequential tasks with dependencies
- Same-file edits
- Routine, low-complexity work (use a single session or a subagent instead)

## Starting a team

Just describe the task and roles in natural language — no setup step required (as of v2.1.178+):

```
Spawn three teammates to explore this from different angles:
one on UX, one on technical architecture, one playing devil's advocate.
```

Claude decides headcount unless you specify it:
```
Spawn 4 teammates to refactor these modules in parallel. Use Sonnet for each.
```

You stay in control — Claude proposes teammates for complex tasks but won't spawn without approval.

## Controlling teammates

- **Agent panel** (below prompt input): ↑/↓ select a teammate, Enter opens its transcript / lets you message it, Escape interrupts its turn.
- Idle teammate rows auto-hide after 30s (still running/addressable — message by name to bring back).
- **Display modes** (`teammateMode` setting): `"in-process"` (default, any terminal), `"auto"` (split panes if already in tmux/iTerm2), `"tmux"` (force split panes via tmux or iTerm2 `it2` CLI). Split panes need tmux or iTerm2 — not supported in VS Code terminal, Windows Terminal, or Ghostty.
- **Plan-approval gate**: "Spawn an architect teammate... Require plan approval before they make any changes." Teammate works read-only until lead approves; give the lead criteria (e.g. "only approve plans with test coverage") since approval is autonomous.
- **Direct messaging**: any teammate can be messaged by name; reach multiple recipients by sending one message per name.
- **Tasks**: shared list with pending/in-progress/completed states + dependencies. Lead assigns explicitly, or teammates self-claim unblocked work. File-locked to avoid race conditions.
- **Shutdown**: "Ask the researcher teammate to shut down" — sends a request the teammate can accept or reject with explanation. Team dirs clean up automatically on session end.
- **Quality gates via hooks**: `TeammateIdle`, `TaskCreated`, `TaskCompleted` — exit code 2 from the hook blocks the action and sends feedback back.

## Reusable roles via subagent definitions

Reference an existing subagent type by name when spawning:
```
Spawn a teammate using the security-reviewer agent type to audit the auth module.
```
Teammate inherits that definition's `tools` allowlist and `model`; the definition body is appended as extra system-prompt instructions (not a replacement). `SendMessage` and task tools are always available regardless of `tools` restrictions. Note: a subagent definition's `skills` and `mcpServers` frontmatter are **not** applied to teammates — teammates load skills/MCP servers from project/user settings like a normal session.

## Architecture notes

- Team forms when first teammate spawns; main session becomes lead for the session's lifetime (no promoting/transferring lead).
- One team per session, no nested teams (teammates can't spawn their own teammates).
- Stored locally: team config `~/.claude/teams/{team-name}/config.json` (session-derived name, removed on session end), task list `~/.claude/tasks/{team-name}/` (persists, governed by `cleanupPeriodDays`). Don't hand-edit the team config — it's overwritten on state updates.
- No project-level team config equivalent — a `.claude/teams/teams.json` in-repo is just an ordinary file, not recognized config.
- Teammates load CLAUDE.md, MCP servers, skills fresh at spawn — they do **not** inherit the lead's conversation history. Always put task-specific context in the spawn prompt.
- Permissions: teammates start with the lead's permission mode (including `--dangerously-skip-permissions` if the lead has it). Can change individual teammate modes after spawn, not at spawn time.

## Best practices (from the docs)

1. **Front-load context in the spawn prompt** — teammates don't see prior conversation.
2. **Team size**: start with 3–5 teammates. Token cost scales linearly per teammate; coordination overhead grows; returns diminish past a point. Three focused teammates often beat five scattered ones.
3. **Task sizing**: aim for 5–6 tasks per teammate. Too small → coordination overhead dominates. Too large → teammates run long without check-ins, risking wasted work. Right-sized = a function, a test file, a review — a clear deliverable.
4. **Don't let the lead "just do it itself"** — if it starts implementing instead of delegating/waiting, say: "Wait for your teammates to complete their tasks before proceeding."
5. **Start with research/review tasks** before attempting parallel implementation — same value, less coordination risk.
6. **Avoid file conflicts** — partition file ownership across teammates explicitly.
7. **Monitor and steer actively** — don't let a team run unattended for long; check in, redirect, synthesize as findings arrive.

## Known limitations

- No session resumption for in-process teammates (`/resume`/`/rewind` don't restore them — lead may try messaging dead teammates; tell it to respawn).
- Task status can lag (teammates sometimes fail to mark complete, blocking dependents) — check manually if something looks stuck.
- Shutdown isn't instant (teammates finish current tool call/request first).
- Split panes unsupported in VS Code integrated terminal, Windows Terminal, Ghostty.

## Troubleshooting quick reference

- **Teammates not appearing**: check agent panel (↑/↓ + Enter); confirm task was complex enough that Claude chose to spawn; for split panes confirm `which tmux` or iTerm2 `it2`+Python API enabled.
- **Too many permission prompts**: pre-approve common ops in permission settings before spawning.
- **Teammate stuck/erroring**: open its transcript, give direct instructions, or spawn a replacement.
- **Lead declares done too early**: tell it to keep going / wait for teammates.
- **Orphaned tmux sessions**: `tmux ls` then `tmux kill-session -t <name>`.

## Decision checklist for this project

Before spawning a team, confirm:
- [ ] Task splits into genuinely independent pieces (not sequential/dependent)
- [ ] Each teammate can own distinct files (no overlap)
- [ ] Worth the token cost vs. a single session or subagent
- [ ] 3–5 teammates, each with ~5–6 right-sized tasks
- [ ] Spawn prompt includes full task-specific context (teammates get no conversation history)
- [ ] Plan to actively monitor rather than fire-and-forget
