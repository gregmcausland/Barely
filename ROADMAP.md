# ROADMAP.md

Implementation plan for Barely task manager.

**Status**: Phase 8 complete, Phase 7 polish in progress

---

## Philosophy

Build in order of dependency:
1. Data layer first (can't do anything without storage)
2. Core business logic (reusable across all UIs)
3. CLI (easier to test, validate core works)
4. REPL (the main interface, builds on CLI patterns)
5. Enhanced features (after basic workflow is solid)
6. Polish and nice-to-haves (Blitz mode, etc.)

Each phase should result in a **usable** increment. No half-finished features.

---

## Phase 1: Foundation

**Goal**: Database setup and core data models working.

### Tasks
- [x] Define project structure and documentation
- [x] Create database schema (`db/schema.sql`)
  - Tasks table
  - Projects table
  - Columns table
  - Indexes for common queries
- [x] Implement models (`core/models.py`)
  - Task dataclass with `from_row()` method
  - Project dataclass
  - Column dataclass
  - JSON serialization for each
- [x] Database connection management (`core/repository.py`)
  - `get_connection()` with proper path handling
  - Auto-create database on first run
  - Execute schema if tables don't exist
- [x] Basic repository CRUD for tasks
  - `create_task(title, column_id, project_id=None) -> Task`
  - `get_task(task_id) -> Task | None`
  - `list_tasks() -> List[Task]`
  - `update_task(task) -> None`
  - `delete_task(task_id) -> None`

**Definition of Done**: Can create, read, update, delete tasks via direct repository calls. Database persists between runs. ✅ **COMPLETE**

---

## Phase 2: Core Service Layer

**Goal**: Business logic that enforces rules and handles errors.

### Tasks
- [x] Define exceptions (`core/exceptions.py`)
  - `BarelyError` base class
  - `TaskNotFoundError`
  - `ProjectNotFoundError`
  - `ColumnNotFoundError`
  - `InvalidInputError`
- [x] Implement core service functions (`core/service.py`)
  - `create_task(title, project_id, column_id) -> Task`
  - `complete_task(task_id) -> Task`
  - `list_tasks(project_id=None, status=None) -> List[Task]`
  - `update_task_title(task_id, new_title) -> Task`
  - `delete_task(task_id) -> None`
- [x] Add default columns on first run
  - "Todo", "In Progress", "Done" columns
  - Auto-create if database is new

**Definition of Done**: Service layer validates input, enforces business rules, raises specific errors. All functions have proper docstrings and type hints. ✅ **COMPLETE**

---

## Phase 3: Minimal CLI

**Goal**: One-shot commands for all core operations.

### Tasks
- [x] Set up Typer app (`cli/main.py`)
  - Basic app structure
  - Version command
  - Help text
- [x] Implement core commands
  - `barely add "task title"` - create task
  - `barely ls` - list tasks
  - `barely done <id>` - complete task
  - `barely rm <id>` - delete task
  - `barely edit <id> "new title"` - update title
- [x] Add output formatting
  - Rich console for colored output
  - `--json` flag for all commands
  - `--raw` flag for plain text
- [x] Error handling
  - Catch service exceptions
  - Display user-friendly error messages
  - Proper exit codes

**Definition of Done**: Can manage tasks entirely from command line. All commands work, handle errors gracefully, and support JSON output for scripting. ✅ **COMPLETE**

---

## Phase 4: Basic REPL

**Goal**: Interactive shell with history and autocomplete.

### Tasks
- [x] Set up prompt-toolkit REPL (`repl/main.py`)
  - Basic prompt loop
  - Command history
  - Exit on Ctrl+D or "exit" command
  - Fallback to simple input() when TTY unavailable
- [x] Command parser (`repl/parser.py`)
  - Parse user input into command + args
  - Handle quoted arguments for task titles
  - Support both positional args and flags
- [x] Implement REPL commands
  - Same verbs as CLI: `add`, `ls`, `done`, `rm`, `edit`
  - Call service layer (not CLI layer)
  - Rich formatting for output
- [x] Basic autocomplete (`repl/completer.py`)
  - Command names
  - Common flags (--json, --raw, --status)
  - Status values (todo, done, archived)
- [x] Success feedback
  - Short confirmation messages
  - Don't clutter the terminal
- [x] CLI integration
  - `barely repl` command to launch REPL
- [x] Test suite
  - All commands tested
  - Parser and completer tested
  - Error handling verified

**Definition of Done**: REPL starts, accepts commands, shows results nicely formatted. Autocomplete suggests commands. History works. Feels responsive. ✅ **COMPLETE**

---

## Phase 5: Projects and Organization

**Goal**: Tasks can be organized into projects and columns.

### Tasks
- [x] Repository layer for projects
  - `create_project(name) -> Project`
  - `list_projects() -> List[Project]`
  - `get_project(project_id) -> Project | None`
  - `delete_project(project_id) -> None`
- [x] Repository layer for columns
  - `create_column(name, position) -> Column`
  - `list_columns() -> List[Column]`
  - `get_column(column_id) -> Column | None`
  - `get_column_by_name(name) -> Column | None`
  - `move_task(task_id, column_id) -> Task`
- [x] Service layer extensions
  - `create_project(name) -> Project`
  - `list_projects() -> List[Project]`
  - `delete_project(project_id) -> None`
  - `move_task(task_id, column_id) -> Task`
  - `list_tasks_by_project(project_id) -> List[Task]`
  - `list_tasks_by_column(column_id) -> List[Task]`
  - `list_columns() -> List[Column]`
- [x] CLI commands
  - `barely project add "name"` - create project
  - `barely project ls` - list projects
  - `barely project rm <id>` - delete project
  - `barely mv <task_id> <column>` - move task to column
  - `barely add --project <name>` - create task with project
  - `barely ls --project <name>` - filter by project
- [x] REPL integration
  - Add project commands (project add, project ls, project rm)
  - Add mv command for moving tasks
  - Updated help command

**Definition of Done**: Can create projects, organize tasks by project, move tasks between columns. Both CLI and REPL support these operations. ✅ **COMPLETE**

---

## Phase 6: Pull-Based Workflow (Backlog → Week → Today)

**Goal**: Enable a just-in-time, commitment-based workflow for managing cognitive load.

### Philosophy: Pull, Don't Schedule

Barely is NOT a calendar or planning tool. It's about:
1. **Unloading** - Dump everything into backlog (get it out of your head)
2. **Committing** - Pull tasks into your weekly scope (Monday planning)
3. **Focusing** - Pull tasks into today's work (daily focus)
4. **Executing** - Hit blitz mode and get it done

Three simple scopes:
- **Backlog**: Everything you might do someday (the inbox)
- **Week**: What you've committed to THIS week (not a date, a commitment)
- **Today**: What you're doing TODAY (your focus list)

Tasks don't auto-move based on dates. YOU pull them through the system when YOU'RE ready.

### The Daily Ritual

**Monday Morning:**
```bash
$ barely backlog
# See everything you could do

$ barely pull 15,23,42 week
# Commit to 3 tasks for this week
```

**Every Morning:**
```bash
$ barely week
# See this week's commitments

$ barely pull 15,23 today
# Pull 2 tasks into today's focus

$ barely blitz
# Enter focused execution mode
```

**Throughout the Day:**
```bash
$ barely today
# What am I supposed to be doing?

$ barely done 15,23
# Mark today's work complete

$ barely pull 42 today
# Pull another from the week if needed
```

This is about COMMITMENT, not SCHEDULING. The act of pulling a task IS the planning.

### Tasks
- [x] Database schema updates
  - Add `scope` TEXT field to tasks table (values: 'backlog', 'week', 'today')
  - Default = 'backlog' (everything starts in backlog)
  - Migration to add column to existing database
- [x] Repository layer enhancements
  - `list_tasks_by_scope(scope: str) -> List[Task]`
  - `update_task_scope(task_id, scope: str) -> Task`
  - Scopes: 'backlog', 'week', 'today'
- [x] Service layer for scope management
  - `list_backlog() -> List[Task]` - scope='backlog'
  - `list_week() -> List[Task]` - scope='week'
  - `list_today() -> List[Task]` - scope='today'
  - `pull_task(task_id, target_scope: str) -> Task` - move task to new scope
  - `pull_tasks(task_ids: List[int], target_scope: str) -> List[Task]` - bulk pull
- [x] CLI commands
  - `barely add "task"` - creates in backlog (default)
  - `barely pull <id>[,<id>...] today|week|backlog` - pull tasks into scope
  - `barely today` - show today's tasks
  - `barely week` - show this week's tasks
  - `barely backlog` - show backlog tasks
- [x] REPL integration
  - `pull 15,23,42 today` - pull multiple tasks into today
  - `pull 15 week` - pull one task into week
  - `today` - view today's focus
  - `week` - view week's commitments
  - `backlog` - view backlog inbox
- [x] Display enhancements
  - Show scope in task listings
  - Color-code by scope:
    - today = bright_magenta (urgent focus)
    - week = blue (committed)
    - backlog = dim (inbox)
  - Count tasks per scope in output

### Workflow Examples

```bash
# Capture everything (defaults to backlog)
barely add "Review PR"
barely add "Write docs"
barely add "Plan sprint"
barely add "Research new framework"

# Monday morning: Plan the week
barely backlog                    # See everything
barely pull 1,2,3 week            # Commit to 3 tasks this week

# Tuesday morning: Focus today
barely week                       # See week's commitments
barely pull 1,2 today             # Pull 2 tasks into today's focus

# During the day
barely today                      # What should I be doing?
barely done 1,2                   # Mark today's work complete
barely pull 3 today               # Pull another from week if I have time

# Uncommit if needed
barely pull 15 backlog            # Send task back to backlog (not ready)
```

### REPL Workflow

```
> add "Fix critical bug"
✓ Created task 1: Fix critical bug (backlog)

> add "Write tests" --today
✓ Created task 2: Write tests (today)

> backlog
Backlog (Inbox)
┌────┬───────────────────┐
│ ID │ Title             │
├────┼───────────────────┤
│ 1  │ Fix critical bug  │
└────┴───────────────────┘

> pull 1 today
✓ Pulled task 1 into today

> today
Today's Focus
┌────┬───────────────────┐
│ ID │ Title             │
├────┼───────────────────┤
│ 1  │ Fix critical bug  │
│ 2  │ Write tests       │
└────┴───────────────────┘

> blitz
# Enter focused execution mode...
```

### Why This Works

**Cognitive Load Management:**
- Backlog = "out of my head, into the system"
- Week = "I can think about these"
- Today = "this is ALL I think about"

**Just-In-Time Planning:**
- No dates to maintain
- No "overdue" tasks to feel bad about
- YOU decide when to commit, based on current reality

**Natural Workflow:**
- Mirrors how people actually work
- Pull-based (like kanban), not push-based (like calendar)
- Scope is a commitment, not a prediction

**Definition of Done**: Tasks can be pulled through scope levels (backlog → week → today). Default behavior captures to backlog. Views are scope-filtered. The `pull` command is the primary workflow tool. ✅ **COMPLETE**

---

## Phase 7: REPL Polish

**Goal**: Make REPL feel great to use daily.

### Tasks
- [ ] Enhanced autocomplete
  - Project names from database
  - Column names from database
  - Smart suggestions based on context
- [ ] Inline pickers (`repl/pickers.py`)
  - When task ID is ambiguous, show picker
  - When project name is ambiguous, show picker
  - Small overlay, doesn't take over screen
- [ ] Better output formatting
  - Tables for task listings
  - Color coding by status/priority
  - Relative dates ("2 hours ago", "tomorrow")
- [ ] Undo support
  - Track last operation
  - `undo` command reverses it (simple cases only)
- [ ] REPL-specific helpers
  - `help` - show available commands
  - `clear` - clear screen
  - Status bar showing current project/filters

**Definition of Done**: REPL feels polished and responsive. Autocomplete is helpful. Output is easy to scan. Small quality-of-life features make it pleasant to use.

---

## Phase 8: Blitz Mode

**Goal**: Focused task completion mode within REPL.

### Tasks
- [x] Blitz mode entry (`repl/blitz.py`)
  - `blitz` command enters mode
  - Loads today's tasks or specified filter
  - Sets up keybindings
- [x] Task display
  - Rich panel showing current task
  - Progress bar (X/Y tasks complete)
  - Live audio waveform visualization (bonus!)
  - Clear, focused layout
- [x] Keybindings
  - `d` - mark done, advance to next
  - `s` - skip to next task
  - `q` - quit blitz mode back to REPL
  - `?` - show full task details
- [x] Visual feedback
  - Update progress in real-time
  - Celebration on completing all tasks
  - Summary stats when exiting (X tasks done in Y minutes)
  - Strikethrough for completed tasks in list

**Definition of Done**: `blitz` command works, shows tasks one at a time, feels focused and motivating. Stays in terminal, returns cleanly to REPL. ✅ **COMPLETE**

---

## Phase 9: Polish and Extras

**Goal**: Nice-to-haves that improve experience.

### Tasks
- [ ] Better date handling
  - `add "task" --due tomorrow`
  - `add "task" --due friday`
  - Natural language date parsing
- [ ] Task priorities
  - `add "task" --priority high`
  - `ls --priority high`
  - Visual indicators in output
- [ ] Task descriptions
  - `add "title" --desc "longer description"`
  - `show <id>` - display full task details
- [ ] Recurring tasks
  - `add "task" --repeat daily`
  - Auto-create next instance on completion
- [ ] Configuration file
  - `~/.barely/config.toml`
  - Default project, column settings
  - Display preferences
- [ ] Import/export
  - `barely export --json > backup.json`
  - `barely import backup.json`

**Definition of Done**: TBD - These are nice-to-haves. Only add if they clearly improve daily usage.

---

## Future Considerations

Features that might be useful but aren't planned yet:

- Tags/labels for cross-project organization
- Task dependencies ("blocked by task X")
- Time tracking integration
- Sync between machines (complex, maybe never)
- Web view for read-only access
- Calendar integration
- Notifications/reminders

**Decision criteria**: Does this improve everyday task flow? Is it the simplest version? Can it wait?

---

## How to Use This Roadmap

1. **Work through phases in order** - each builds on the previous
2. **Update status as you go** - mark tasks complete with [x]
3. **Add notes for decisions** - if you change approach, document why
4. **Skip or defer freely** - if a feature doesn't feel right, mark it and move on
5. **Keep "Definition of Done" honest** - phase is done when that statement is true

Current focus: **Phase 7 - REPL Polish** (finishing touches)

Phase 1 complete! Foundation working with database and repository layer.
Phase 2 complete! Service layer with validation and business rules.
Phase 3 complete! CLI with all core commands, error handling, and JSON output.
Phase 4 complete! Interactive REPL with autocomplete, history, and rich formatting.
Phase 5 complete! Projects and organization - tasks can be organized by project and moved between columns.
Phase 6 complete! Pull-based workflow - tasks flow through backlog → week → today scopes.
Phase 7 mostly complete! Context system, smart pickers, animations, toolbar. Need: dynamic autocomplete, descriptions.
Phase 8 complete! Blitz mode with audio visualization, keyboard controls, and focused task flow.

---

### END OF FILE
