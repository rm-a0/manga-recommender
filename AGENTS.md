# AGENTS.md

Instructions for AI coding agents (Claude Code, Cursor, Codex, etc.) working in this repository.

## What this project is

A manga recommendation engine, maintained partly as a hand-coding practice project.
**The process of writing the backend code matters as much as the code itself** — so
this repo has a deliberately unusual collaboration contract with AI agents. Read it
before touching anything, whether you're an AI agent or a human contributor.

## Collaboration contract

### Hand-coded only — do not write or edit this for the user

- `src/` application/backend code: FastAPI routers and endpoints, services, DB models,
  ingestion/pipeline logic, recommendation logic.
- **Agent's role here: discussion partner, explainer, and reviewer only.** Explain
  concepts, review diffs, flag bugs and design issues, suggest best practices, verify
  behavior (run linters/tests/queries). Do not write the implementation, even if asked
  to "just fix it quickly" — point out the fix and let the user fix and understand it.

### Agent-codable, but must follow best practices for the stack in use

- Frontend / client-side UI code only (the view layer — components, markup, styling,
  client-side state). This is an explicit exception because frontend isn't this
  project's learning focus.
- **Not included in this exception**: the FastAPI routers/endpoints that serve the UI —
  those are backend `src/` code and stay hand-coded per the rule above.
- "Best practices" means idiomatic, conventional code for whatever frontend framework
  is chosen (not yet decided as of this writing) — proper component structure,
  accessibility, no inline-everything, type safety if the stack uses it. If a shortcut
  or non-idiomatic pattern seems necessary, flag it to the user instead of silently
  taking it.

### Docstrings — agent-written, using Simplified Technical English

Unlike the rest of backend `src/` code, docstrings themselves are fine for an agent to
write or generate directly, even inside otherwise hand-coded files — this is a narrow
exception to the "hand-coded only" rule above, scoped to docstrings only (not the
surrounding code, not comments elsewhere).

Follow Simplified Technical English (ASD-STE100) principles, adapted for code — not
literal compliance with the full approved-word dictionary, which is impractical for
technical Python code:

- One idea per sentence. Short sentences.
- Active voice, imperative mood for the summary line ("Return the parsed record," not
  "Returns the parsed record" or "This function returns...").
- No idioms, no filler words, no restating what's already obvious from the function
  name, parameter names, or type hints.
- Length: a one-sentence summary (roughly under 100 characters) is the default. Add a
  second short sentence only for a genuinely non-obvious behavior, edge case, or
  constraint — never pad length for its own sake.

### Pair on it — propose incrementally, don't hand over finished files unprompted

- Infra/scaffolding: CI/CD YAML, Makefile, Dockerfile, deployment config, README,
  `pyproject.toml` build/tooling config, Alembic `env.py` wiring, `.env`/config
  structure.
- Propose a snippet or approach, explain the why, let the user decide or tweak it.
  Don't generate a complete finished file in one shot.

### Git — read-only for agents, always

Agents must not run any git command that changes repo state: no `commit`, `push`,
`pull`, `merge`, `rebase`, `branch` creation/deletion, `tag`, `stash`, `checkout`/`reset`
that alters files, etc. The user performs all of these manually, every time — not just
when unattended.

Read-only inspection is fine and encouraged: `status`, `diff`, `log`, `show`, `branch`
(listing), `blame`. Use these freely to understand state before proposing changes.

### If unsure which bucket something falls into

Ask the user rather than assuming. Getting this wrong defeats the point of the project.

## Keeping this file current

This is a living document — update it as the collaboration model evolves (e.g. once a
frontend framework is chosen, once new project areas exist). Don't let it go stale.
