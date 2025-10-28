# Repository Guidelines

## Project Structure & Module Organization
- Source: `barely/` — `core/` (models, repository, service), `cli/` (Typer commands), `repl/` (interactive shell, pickers, blitz).
- Tests: `test_*.py` in repo root (script-style; runnable via pytest).
- Data: SQLite DB at `~/.barely/barely.db`; schema in `db/schema.sql`.
- Entrypoints: `barely` (console script), `barely.bat` (Windows), or `python -m barely.cli.main`.

## Build, Test, and Development Commands
- Install editable: `pip install -e .` (installs CLI `barely` and deps).
- Run CLI: `barely` (launch REPL) or `barely ls`, `barely add "Task"`.
- Run as module: `python -m barely.cli.main ...`.
- Tests: `pytest -q` (runs `test_*.py`).
- Migration helper: `python run_migration.py` (advanced; updates schema/data as needed).

## Coding Style & Naming Conventions
- Python 3.10+, PEP 8, 4‑space indentation, type hints where practical.
- Modules/functions: `snake_case`; classes: `PascalCase`; constants: `UPPER_SNAKE_CASE`.
- Keep layers clean: CLI/REPL → service → repository → SQLite. Do not bypass layers.
- CLI output via `rich`; send errors to stderr (see `barely/cli/main.py`).
- Small, focused functions; avoid side effects in `core/`.

## Testing Guidelines
- Framework: pytest. Place new tests as `test_*.py` in repo root to match existing pattern.
- Prefer service‑level tests; mock DB only when necessary. Use real SQLite file created in `~/.barely` for integration tests.
- Name tests descriptively (e.g., `test_pull_workflow_today()`); assert behavior, not implementation.
- Run: `pytest -q`. Ensure tests pass locally before opening a PR.

## Commit & Pull Request Guidelines
- Commits: imperative mood, concise subject, scoped prefix when useful (e.g., `cli: add pull command`, `core/service: validate scope`).
- PRs must include: clear description, rationale, screenshots or terminal output for UX changes, and links to related items in `ROADMAP.md`/`STATUS.md`.
- Checklist: passes `pytest`, no layer violations, no breaking changes to documented CLI.

## Security & Configuration Tips
- DB path: `~/.barely/barely.db`. Do not commit local DB files. Back up before running migrations.
- Avoid printing secrets or paths in logs. Respect Windows encoding handling present in CLI.
