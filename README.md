# Barely

A minimalist, terminal-native task manager built around **pull-based workflows** and **keyboard-first interaction**. Work the way you actually think, not the way some app thinks you should.

## Philosophy

Barely is designed around how you actually work:

- **Pull, don't schedule**: Move tasks through scope levels (backlog → week → today) when YOU'RE ready, not based on dates
- **REPL-first**: Interactive shell as the primary interface—where the magic happens
- **Context-aware**: Set your working project/scope and all commands adapt automatically
- **Fast feedback**: Instant responses, delightful animations, keyboard-native UX
- **Local-first**: SQLite storage, no cloud dependencies, your data stays yours

## Installation

### Option 1: Install with pip (recommended)
```bash
pip install -e .
```
This installs the `barely` command globally.

### Option 2: Run as Python module (no installation)

**Windows:**
```bash
# Use the wrapper script
barely.bat add "Write documentation"

# Or run directly as module
python -m barely.cli.main add "Write documentation"
```

**Unix/Linux/Mac:**
```bash
# Make the wrapper executable (one time only)
chmod +x barely

# Use the wrapper script
./barely add "Write documentation"

# Or run directly as module
python -m barely.cli.main add "Write documentation"
```

## Quick Start

```bash
# Launch interactive REPL (recommended)
barely

# Or use one-shot commands
barely add "Write documentation"
barely ls
barely done 1
```

## The Pull-Based Workflow

Barely uses a **three-scope system** that matches how you actually think about work:

### 1. Backlog (The Inbox)
Everything starts here. Capture tasks without worrying about when you'll do them.

```bash
barely add "Fix critical bug"
barely add "Write tests"
barely add "Plan sprint"
```

### 2. Week (Your Commitment)
Pull tasks from backlog when you're ready to commit to them THIS week.

```bash
barely backlog                # See everything
barely pull 1,2,3 week        # Commit to 3 tasks
```

### 3. Today (Your Focus)
Pull tasks from week into today's focus list. This is what you're ACTUALLY working on.

```bash
barely week                   # See week's commitments
barely pull 1,2 today         # Pull 2 tasks into today
barely today                  # What should I be doing?
```

### The Daily Ritual

**Monday Morning:**
```bash
barely backlog               # Review everything
barely pull 15,23,42 week    # Commit to this week
```

**Every Morning:**
```bash
barely week                  # See commitments
barely pull 15,23 today      # Focus for today
barely blitz                 # Enter focused mode
```

**Throughout the Day:**
```bash
barely today                 # What am I working on?
barely done 15,23            # Mark work complete
barely pull 42 today         # Pull another if needed
```

## Core Commands

### Task Management
```bash
barely add "Task title"              # Create task (goes to backlog)
barely ls                            # List all tasks
barely ls --status todo              # Filter by status
barely ls --project Work             # Filter by project
barely done 1                        # Complete task
barely done 1,2,3                    # Complete multiple
barely rm 5                          # Delete task
barely edit 1 "New title"            # Update title
```

### Scope Management (Pull Workflow)
```bash
barely backlog                       # View backlog
barely week                          # View this week
barely today                         # View today
barely pull 1 today                  # Pull task into today
barely pull 2,3,4 week              # Pull multiple into week
barely pull 5 backlog               # Defer back to backlog
```

### Project Organization
```bash
barely project add "Work"            # Create project
barely project ls                    # List projects
barely project rm 2                  # Delete project
barely mv 5 "In Progress"           # Move task to column
```

### Focused Execution
```bash
barely blitz                         # Enter blitz mode
                                     # - Shows tasks one at a time
                                     # - Live audio waveform viz
                                     # - d=done, s=skip, q=quit
```

## Interactive REPL

The REPL is where Barely shines. Launch with `barely` or `barely repl`.

### Persistent Context

Set your working context and all commands adapt automatically:

```bash
barely> use Work                     # Set project context
barely:[Work]> add Fix bug           # Creates in Work project

barely:[Work]> scope today           # Filter to today's scope
barely:[Work | today]> ls            # Shows only Work tasks in today

barely:[Work | today]> done          # Smart picker shows only relevant tasks
```

### Smart Pickers

When you don't specify a task ID, Barely shows an interactive picker:

```bash
barely> done
Select tasks to mark as done (enter number or comma-separated list, or press Enter to cancel):
  1. Fix authentication bug
  2. Write unit tests
  3. Update documentation
Enter selection: 1,3

✓ Completed: Fix authentication bug
✓ Completed: Update documentation
```

Pickers respect your context and only show relevant tasks!

### Features

- **Command history**: Up/down arrows to navigate
- **Autocomplete**: Tab key for commands, flags, and values
- **Bottom toolbar**: Real-time task counts and rotating tips
- **Right prompt**: Shows task count in current context
- **ASCII animations**: Delightful feedback for operations
- **Clear command**: `clear` to clean up cluttered output
- **Exit**: Ctrl+D or type `exit`/`quit`

### REPL Commands

All CLI commands work in REPL, plus:
- `use <project>` / `use none` - Set/clear project context
- `scope <scope>` / `scope all` - Set/clear scope filter
- `help` - Show all commands
- `clear` - Clear screen
- `blitz` - Enter focused task completion mode

## Blitz Mode

**Focused task completion with audio visualization.**

```bash
barely blitz
```

Blitz mode shows tasks from your today scope one at a time with:
- Live audio waveform visualization
- Keyboard controls (d=done, s=skip, ?=details, q=quit)
- Progress tracking with strikethrough
- Celebration on completion

Perfect for getting into flow and crushing your daily list.

## Output Formats

All commands support machine-readable output:

```bash
barely ls --json                     # JSON output for scripting
barely ls --raw                      # Plain text, no colors
```

## Project Status

**Version 0.3.0** - Phases 1-8 complete, Phase 7 polish ongoing

✅ **Complete:**
- Phase 1: Foundation (SQLite, models, repository)
- Phase 2: Service layer (business logic, validation)
- Phase 3: CLI (Typer commands, JSON output)
- Phase 4: REPL (prompt-toolkit, autocomplete)
- Phase 5: Projects & organization
- Phase 6: Pull-based workflow (backlog/week/today)
- Phase 7: REPL polish (context, pickers, animations, toolbar) - 90% complete
- Phase 8: Blitz mode (audio viz, keyboard controls)

🚧 **In Progress:**
- Dynamic autocomplete (project/column names from DB)
- Task descriptions
- Relative date display

See [ROADMAP.md](ROADMAP.md) for full development plan and [STATUS.md](STATUS.md) for detailed progress.

## Documentation

- [ROADMAP.md](ROADMAP.md) - Implementation plan and progress
- [CLAUDE.md](CLAUDE.md) - Architecture and development guidelines
- [STATUS.md](STATUS.md) - Detailed current status and session history

## Architecture

```
REPL/CLI (UI Layer)
    ↓
Service Layer (Business Logic)
    ↓
Repository Layer (Data Access)
    ↓
SQLite Database (~/.barely/barely.db)
```

Clean separation of concerns makes the codebase easy to understand and extend.

## Requirements

- Python 3.10+
- Dependencies (auto-installed with pip):
  - typer (CLI framework)
  - rich (formatted output)
  - prompt-toolkit (interactive REPL)
  - numpy (audio processing for blitz mode)
  - pyaudiowpatch (Windows audio capture for blitz mode)

## License

MIT

## Why "Barely"?

Because you barely need anything else. No cloud sync, no subscription, no complex features you'll never use. Just fast, local, keyboard-native task management that works the way you think.
