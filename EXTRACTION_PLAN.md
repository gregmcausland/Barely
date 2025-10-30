# File Extraction Plan: Splitting Monolithic Files

## Overview

This plan outlines how to extract commands from the two large monolithic files:

- `barely/cli/main.py` (1488 lines) → Split into command modules
- `barely/repl/main.py` (2170 lines) → Split into command handlers + UI modules

## Goals

1. **Reduce file sizes** - Each module < 500 lines
2. **Improve organization** - Logical grouping of related commands
3. **Maintain functionality** - No behavior changes
4. **Preserve imports** - Clean dependency structure
5. **Shared utilities** - Common code extracted to helpers

---

## Part 1: CLI Structure (`barely/cli/main.py` → modules)

### Current Structure Analysis

**Commands in main.py:**

- Task commands: add, ls, done, rm, edit, desc, show, mv, assign (9 commands)
- Workflow commands: today, week, backlog, archive, pull (5 commands)
- Project commands: project_add, project_ls, project_rm (3 commands)
- System commands: version, help, repl, blitz (4 commands)
- **Total: 21 commands**

**Shared dependencies:**

- `console`, `error_console` (Rich Console instances)
- `app`, `project_app` (Typer apps)
- `service`, `repository` (core modules)
- Exception classes
- `improve_title_with_ai` utility

### Proposed Structure

```
barely/cli/
├── __init__.py                 # Package exports
├── main.py                     # ~200 lines: App setup, entry point, default callback
├── commands/
│   ├── __init__.py            # Export all commands
│   ├── tasks.py               # ~400 lines: add, ls, done, rm, edit, desc, show, mv, assign
│   ├── workflow.py            # ~300 lines: today, week, backlog, archive, pull
│   ├── projects.py            # ~250 lines: project_add, project_ls, project_rm
│   └── system.py              # ~200 lines: version, help, repl, blitz
└── formatting.py              # Shared formatting utilities (if not already extracted)
```

### Implementation Steps

1. **Create commands directory structure**

   - Create `barely/cli/commands/__init__.py`
   - Create empty command modules: `tasks.py`, `workflow.py`, `projects.py`, `system.py`

2. **Extract task commands** (`tasks.py`)

   - Move: `add()`, `ls()`, `done()`, `rm()`, `edit()`, `desc()`, `show()`, `mv()`, `assign()`
   - Import shared dependencies: `console`, `error_console`, `service`, exceptions
   - Import `improve_title_with_ai` from utils
   - Export functions with `@app.command()` decorators

3. **Extract workflow commands** (`workflow.py`)

   - Move: `today()`, `week()`, `backlog()`, `archive()`, `pull()`
   - Share formatting utilities
   - Export functions with `@app.command()` decorators

4. **Extract project commands** (`projects.py`)

   - Move: `project_add()`, `project_ls()`, `project_rm()`
   - These are already in `project_app` subcommand group
   - Export functions with `@project_app.command()` decorators

5. **Extract system commands** (`system.py`)

   - Move: `version()`, `help()`, `repl()`, `blitz()`
   - Keep simple and focused

6. **Update main.py**

   - Keep: app setup, default callback, console instances
   - Import and register commands from `commands/` modules
   - Reduce to ~200 lines

7. **Update exports**
   - `barely/cli/commands/__init__.py` exports all command functions
   - `barely/cli/__init__.py` exports `app` and `main()`

---

## Part 2: REPL Structure (`barely/repl/main.py` → modules)

### Current Structure Analysis

**Commands in main.py:**

- Task commands: add, ls, done, rm, edit, desc, show, mv, assign (9 commands)
- Workflow commands: today, week, backlog, archive, pull (5 commands)
- Project commands: use, project_add, project_ls, project_rm (4 commands)
- Context commands: scope, clear (2 commands)
- System commands: help, exit, blitz (3 commands)
- **Total: 23 commands**

**Shared components:**

- REPL session setup (`PromptSession`)
- Command parser (`parse_command()`)
- Context management (`current_project`, `current_scope`)
- Formatting functions (`display_tasks_table()`, etc.)
- Picker functions (`pick_task()`, `pick_project()`, etc.)
- Animation system

### Proposed Structure

```
barely/repl/
├── __init__.py                 # Package exports
├── main.py                     # ~400 lines: REPL loop, session setup, command routing
├── commands/
│   ├── __init__.py            # Export all command handlers
│   ├── tasks.py               # ~400 lines: add, ls, done, rm, edit, desc, show, mv, assign handlers
│   ├── workflow.py            # ~300 lines: today, week, backlog, archive, pull handlers
│   ├── projects.py            # ~250 lines: use, project_add, project_ls, project_rm handlers
│   └── system.py              # ~150 lines: help, exit, clear, blitz handlers
├── formatting.py              # Display functions (if not already extracted)
├── pickers.py                 # Already exists - picker functions
├── completer.py               # Already exists - autocomplete logic
├── parser.py                  # Already exists - command parsing
├── style.py                   # Already exists - animations and styling
└── undo.py                    # Already exists - undo system
```

### Implementation Steps

1. **Create commands directory structure**

   - Create `barely/repl/commands/__init__.py`
   - Create empty command handler modules

2. **Extract task command handlers** (`commands/tasks.py`)

   - Move handlers: `handle_add()`, `handle_ls()`, `handle_done()`, etc.
   - Import shared: `service`, `display_tasks_table()`, `pick_task()`, etc.
   - Functions take `(args, context)` and return results

3. **Extract workflow command handlers** (`commands/workflow.py`)

   - Move handlers: `handle_today()`, `handle_week()`, `handle_backlog()`, etc.
   - Share context awareness and formatting

4. **Extract project command handlers** (`commands/projects.py`)

   - Move handlers: `handle_use()`, `handle_project_add()`, etc.
   - Handle context updates

5. **Extract system command handlers** (`commands/system.py`)

   - Move handlers: `handle_help()`, `handle_exit()`, `handle_clear()`, `handle_blitz()`

6. **Update main.py**

   - Keep: REPL loop, session setup, command routing
   - Import handlers from `commands/` modules
   - Route commands to appropriate handlers
   - Maintain context management

7. **Update exports**
   - `barely/repl/commands/__init__.py` exports all handlers
   - `barely/repl/__init__.py` exports `main()` function

---

## Part 3: Shared Utilities

### Formatting Module

Already exists: `barely/formatting.py`

- `TaskFormatter` class
- `parse_task_ids()`, `parse_project_ids()` utilities

### Additional Utilities

Consider extracting to `barely/cli/utils.py` or `barely/repl/utils.py`:

- Shared error handling patterns
- Output formatting helpers
- Argument parsing utilities

---

## Migration Strategy

### Phase 1: CLI Extraction (Lower Risk)

1. Create `commands/` directory and empty modules
2. Extract one command group at a time (start with `system.py` - smallest)
3. Test each extraction thoroughly
4. Update imports in `main.py`
5. Verify all CLI commands still work

### Phase 2: REPL Extraction (Higher Complexity)

1. Create `commands/` directory and empty modules
2. Extract command handlers one group at a time
3. Ensure context management works correctly
4. Test command routing
5. Verify REPL functionality end-to-end

### Testing Checklist

- [ ] All CLI commands work (`barely ls`, `barely add`, etc.)
- [ ] All REPL commands work (interactive mode)
- [ ] Autocomplete still functions
- [ ] Error handling works correctly
- [ ] Output formatting unchanged
- [ ] Context system works (project, scope)
- [ ] Pickers work correctly
- [ ] Animations still display
- [ ] No import errors

---

## Benefits

1. **Easier navigation** - Find commands quickly
2. **Reduced merge conflicts** - Multiple people can work on different command groups
3. **Better testing** - Test command groups in isolation
4. **Clearer structure** - Logical organization
5. **Maintainability** - Smaller files are easier to understand

---

## Notes

- Keep backward compatibility - no API changes
- Maintain existing error handling patterns
- Preserve all formatting and output styles
- Keep context management in main.py for now
- Consider extracting context management later if it grows

---

## Status

**Current State**: Planning phase
**Next Step**: Begin Phase 1 - CLI extraction, starting with `system.py`
