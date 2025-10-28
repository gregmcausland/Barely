# CLAUDE.md

## Project: Barely
A minimalist, terminal-native task manager.

---

## Vision

Barely is CLI-first, REPL-focused, and fullscreen only when it truly helps.
Focus on **speed, clarity, and joy** in the terminal.

Core tenets:
- SQLite local-first (no cloud dependencies)
- REPL as primary interaction mode
- Every operation callable from CLI as one-shot command
- Thin UI layers calling into core business logic
- Fast feedback, keyboard-native UX

---

## Architecture Overview

```
barely/
  core/
    models.py       # Task, Project, Column dataclasses
    repository.py   # SQLite CRUD operations
    service.py      # Business logic layer

  cli/
    main.py         # Typer one-shot commands

  repl/
    main.py         # prompt-toolkit REPL loop
    completer.py    # Autocomplete logic
    pickers.py      # Inline selection helpers
    blitz.py        # Focused task-completion mode (in-REPL)

  db/
    schema.sql      # Database schema
    migrations/     # Schema version management
```

**Data flow**: UI Layer → Service Layer → Repository Layer → SQLite

**Never** put business logic in UI. **Never** access database directly from UI.

---

## Command Flow Pattern

Here's how a command should flow through the system:

### Example: Completing a task

**REPL Layer** (`repl/main.py`)
```python
def handle_command(user_input: str):
    """Parse command, call service, display result."""
    cmd, args = parse_input(user_input)

    if cmd == "done":
        task_id = args.get("id") or pick_task()  # Interactive picker if needed
        result = service.complete_task(task_id)  # Call service
        display_success(f"✓ Completed: {result.title}")  # Display only
```

**Service Layer** (`core/service.py`)
```python
def complete_task(task_id: int) -> Task:
    """Mark task as complete. Returns updated task."""
    task = repository.get_task(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    task.completed_at = datetime.now()
    task.status = "done"

    repository.update_task(task)
    return task
```

**Repository Layer** (`core/repository.py`)
```python
def update_task(task: Task) -> None:
    """Persist task changes to database."""
    conn = get_connection()
    conn.execute(
        "UPDATE tasks SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?",
        (task.status, task.completed_at, datetime.now(), task.id)
    )
    conn.commit()
```

**Key pattern**:
- UI handles parsing and display
- Service handles business rules and validation
- Repository handles database operations
- Each layer returns data, never prints/displays

---

## File Header Pattern (claude-index)

Every Python file must start with a structured comment block for quick LLM context:

```python
"""
FILE: barely/core/service.py
PURPOSE: Business logic layer for task operations
EXPORTS:
  - create_task(title, project_id, column_id) -> Task
  - complete_task(task_id) -> Task
  - move_task(task_id, column_id) -> Task
  - list_tasks(filters: TaskFilter) -> List[Task]
DEPENDENCIES:
  - core.models (Task, Project, Column)
  - core.repository (all CRUD functions)
  - datetime (for timestamps)
NOTES:
  - All functions validate input and raise descriptive errors
  - No direct database access (use repository layer)
  - Returns domain objects, never dicts or raw SQL results
"""
```

**Update this header whenever you**:
- Add/remove exported functions
- Change function signatures
- Add new dependencies
- Change the purpose of the file

This allows reading just the header to understand the file's API without scanning the entire file.

---

## Comment Guidelines

Write comments that help LLMs (and humans) understand code quickly.

### Good comments explain WHY and CONTEXT

```python
# Group tasks by column for efficient rendering
tasks_by_column = defaultdict(list)

# SQLite doesn't support RETURNING clause, so fetch separately
task = repository.get_task(task_id)

# Autocomplete must handle partial matches case-insensitively
# because users type fast and don't use shift
matches = [cmd for cmd in commands if cmd.lower().startswith(partial.lower())]
```

### Bad comments repeat WHAT the code says

```python
# Set status to done
task.status = "done"

# Loop through tasks
for task in tasks:
    ...

# Return the result
return result
```

### Function docstrings: Contract and edge cases

```python
def move_task(task_id: int, column_id: int) -> Task:
    """
    Move task to a different column.

    Validates that both task and column exist before moving.
    Automatically sets updated_at timestamp.

    Raises:
        TaskNotFoundError: If task_id doesn't exist
        ColumnNotFoundError: If column_id doesn't exist
    """
```

### Inline comments: Business rules and tricky logic

```python
# Don't show completed tasks in "today" view unless explicitly filtered
# This keeps the default view focused on actionable items
if filters.today and not filters.include_completed:
    tasks = [t for t in tasks if not t.completed_at]
```

---

## Database Patterns

### Schema Philosophy
- Simple, normalized structure
- Use INTEGER PRIMARY KEY for SQLite optimization
- Store timestamps as ISO-8601 strings for readability
- Use CHECK constraints for data validation at DB level

### Example Schema
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    project_id INTEGER REFERENCES projects(id),
    column_id INTEGER NOT NULL REFERENCES columns(id),
    status TEXT CHECK(status IN ('todo', 'done', 'archived')) DEFAULT 'todo',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_project ON tasks(project_id);
```

### Repository Pattern
- One function per operation
- Return domain objects (dataclasses), not dicts
- Use context managers for connections
- Let exceptions bubble up (service layer handles them)

```python
def get_task(task_id: int) -> Task | None:
    """Fetch single task by ID. Returns None if not found."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()

    return Task.from_row(row) if row else None
```

---

## REPL Implementation

### Use prompt-toolkit for:
- Main REPL loop with history
- Autocomplete (commands, flags, project names)
- Inline pickers (small overlays for selection)
- Keybindings

### Use Rich for:
- Formatted output (tables, panels, progress bars)
- Color and styling
- Live updates (for timers, progress)

### REPL behaviors:
- Execute immediately when command is complete
- Show inline picker only when ambiguous
- Provide short success confirmations
- Keep prompt visible (don't take over screen)

### Blitz Mode (in-REPL focused mode)
A special command that shows tasks one at a time with visual focus:

```python
# User types: blitz
# Shows floating panel with current task, timer, progress
# Stays in terminal, uses Rich panels + prompt-toolkit overlays
# Keybindings: d=done, s=skip, q=quit
# Returns to normal REPL when done
```

**Implementation approach**:
- Use `prompt_toolkit.shortcuts.ProgressBar` or custom layout
- Rich panels for task display
- Real-time updates without clearing screen
- Simple keybinding handler

**Not** a fullscreen TUI takeover. Just a focused view within the REPL.

---

## CLI Implementation

### Use Typer for:
- Command parsing and help text
- Type validation
- Flag/option handling

### Pattern for one-shot commands
```python
@app.command()
def done(
    task_id: int = typer.Argument(..., help="Task ID to complete"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Mark a task as complete."""
    try:
        task = service.complete_task(task_id)

        if json_output:
            print(task.to_json())
        else:
            console.print(f"[green]✓[/green] Completed: {task.title}")

    except TaskNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        raise typer.Exit(1)
```

Every command should support:
- `--json` flag for machine-readable output
- `--raw` flag for plain text (no colors/formatting)
- Meaningful exit codes (0=success, 1=error)

---

## Error Handling

### Define specific exceptions in `core/exceptions.py`
```python
class BarelyError(Exception):
    """Base exception for all Barely errors."""
    pass

class TaskNotFoundError(BarelyError):
    """Task with given ID doesn't exist."""
    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"Task {task_id} not found")

class InvalidColumnError(BarelyError):
    """Column doesn't exist or is invalid."""
    pass
```

### Let exceptions bubble from repository → service → UI
- Repository raises specific errors
- Service catches and adds context if needed
- UI catches and displays user-friendly messages

### UI error display
```python
try:
    result = service.do_something()
except TaskNotFoundError as e:
    console.print(f"[red]Error:[/red] {e}")
except BarelyError as e:
    console.print(f"[red]Unexpected error:[/red] {e}")
```

---

## Adding a New Feature: Checklist

1. **Define the data model** (if needed)
   - Add/update dataclass in `core/models.py`
   - Update schema in `db/schema.sql`
   - Write migration if changing existing schema

2. **Implement repository layer**
   - Add CRUD functions in `core/repository.py`
   - Return domain objects, handle errors
   - Update file header with new exports

3. **Implement service layer**
   - Add business logic in `core/service.py`
   - Validate input, enforce rules
   - Call repository functions
   - Update file header

4. **Add CLI command**
   - Create Typer command in `cli/main.py`
   - Support `--json` and `--raw` flags
   - Handle errors gracefully

5. **Add REPL command**
   - Add parser case in `repl/main.py`
   - Add autocomplete if needed
   - Display results with Rich

6. **Test manually**
   - Try the feature in both CLI and REPL
   - Test error cases
   - Verify output formats

---

## Development Workflow

### When writing code:
1. Start with the data model and repository
2. Build service layer with business rules
3. Add CLI command first (easier to test)
4. Add REPL integration second
5. Keep file headers updated as you go

### When reading code:
1. Read file header to understand API
2. Look at function signatures and docstrings
3. Only dive into implementation if needed

### When modifying code:
1. Update file header if API changes
2. Update related docstrings
3. Check error handling is consistent
4. Test both CLI and REPL paths

---

## What to Build First

See ROADMAP.md for implementation order and current status.

General priority:
1. Core data model + SQLite setup
2. Basic repository layer
3. Essential service functions (create, list, complete)
4. Minimal CLI
5. Basic REPL with autocomplete
6. Enhanced features (projects, columns, filters)
7. Blitz mode (after everything else works)

---

## What NOT to Do

- ❌ Put SQL in service layer (use repository)
- ❌ Put business logic in UI layer
- ❌ Return dicts from repository (use dataclasses)
- ❌ Print directly from service layer (return data)
- ❌ Repeat WHAT code does in comments
- ❌ Add features before core works
- ❌ Build TUI before REPL is solid
- ❌ Add heavy automation or "smart" systems
- ❌ Skip updating file headers when changing APIs

---

## Questions to Ask Before Adding Anything

- Does this improve everyday task flow?
- Is this the simplest version that could work?
- Does this belong in core, service, or UI?
- Can this be done in the REPL without fullscreen?
- Is this discoverable and keyboard-friendly?

**When in doubt, build the simplest version first.**

---

### END OF FILE
