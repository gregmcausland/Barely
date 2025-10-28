# Barely - Current Status

**Last Updated**: 2025-10-26 (Phase 7 progress - continued)
**Version**: 0.2.5 (Phase 7 in progress)
**Overall Progress**: 6.5 of 9 phases complete (72%)

---

## 🆕 This Session (Continued)

**Completed:**
1. ✅ **Improved output formatting** - Project names display in task tables instead of IDs
2. ✅ **Enhanced canvas animations** - Replaced single-line animations with 16x9 multi-line canvas
   - Firework explosion: Rocket launches from bottom (^), rises with trail, explodes at peak with ✓ center
   - Sparkle burst: Star grows from center, expands with radiating particles
   - Poof effect: Smoke dispersing with block shading (█ → ▓ → ▒ → ·)
   - Whoosh movement: Object slides across screen with motion trail
3. ✅ **Doubled animation duration** - Made animations more observable and detailed
   - Increased from 8 frames to 16 frames for firework
   - Increased from 5 frames to 11 frames for sparkle
   - Slowed frame delay from 0.08s to 0.15s for `done`
   - Total animation time: ~2.4 seconds (was ~0.6 seconds)
4. ✅ **Bottom toolbar** - Persistent status bar at bottom of screen ⭐ NEW
   - Shows real-time task counts: `⭐ 3 today | 📅 5 week | 📋 50 backlog`
   - Displays rotating tips (7 tips, changes after each command)
   - Always visible, gray background
5. ✅ **Right prompt** - Task count on right side of input line ⭐ NEW
   - Shows `[120 total]` when no filter active
   - Shows `[45 in view]` when context filter applied
   - Updates dynamically based on project/scope context
   - Unobtrusive gray text
6. ✅ **Clear command** - Clear the screen when it gets cluttered ⭐ NEW
   - Simple `clear` command to clear terminal
   - Useful after multiple list/pull/move operations
   - Added to autocomplete and help
7. ✅ **Improved spacing** - Automatic whitespace after each command ⭐ NEW
   - Adds blank line after command output
   - Makes output more scannable
   - Reduces visual clutter between operations

**Key Changes:**
- Added `service.get_project()` function for project lookup
- Updated `display_tasks_table()` with project name caching
- Rewrote animation system in `style.py` with canvas-based rendering
- Created `_create_canvas()`, `_set_pixel()`, and `_play_canvas_animation()` helpers
- Four detailed animation types with more frames and slower timing
- Uses ANSI terminal codes (\033[9A) to move cursor and redraw frames
- Rocket launches with ^ character, leaves trail, explodes into full burst
- Added `get_bottom_toolbar()` function for status bar display
- Added `get_right_prompt()` function for context-aware task count
- Rotating tips system (7 tips, increments after each command)
- PromptSession now includes `bottom_toolbar` and `rprompt` parameters
- Added `handle_clear_command()` for screen clearing
- Added `clear` to autocomplete and help documentation
- Automatic whitespace (blank line) after each command execution
- All tests passing (Phase 2, 3, 4, context/pickers)

---

## ✅ Completed Phases (1-6)

### Phase 1: Foundation
- SQLite database with tasks, projects, columns
- Core data models (Task, Project, Column)
- Repository layer with CRUD operations
- Database auto-creation on first run

### Phase 2: Core Service Layer
- Business logic layer with validation
- Specific exception types (TaskNotFoundError, etc.)
- Service functions for all core operations
- Default columns created automatically

### Phase 3: Minimal CLI
- Typer-based command-line interface
- All core commands: add, ls, done, rm, edit, mv
- JSON and raw output modes for scripting
- Proper error handling and exit codes

### Phase 4: Basic REPL
- prompt-toolkit interactive shell
- Command history and basic autocomplete
- Command parser with quoted arguments
- Rich formatted output
- Fallback to simple mode when TTY unavailable

### Phase 5: Projects and Organization
- Project management (create, list, delete)
- Task-project associations
- Column-based organization
- Move tasks between columns
- Filter tasks by project
- Bulk operations with comma-separated IDs

### Phase 6: Pull-Based Workflow
- Three-scope system: backlog → week → today
- Pull command to move tasks between scopes
- Scope-specific views (today, week, backlog)
- Color-coded scope display
- Migration tool for existing databases
- All tasks default to backlog scope

### Phase 7: REPL Polish ⭐ **IN PROGRESS**
- ✅ Persistent context system (project + scope)
- ✅ Dynamic prompt showing current context
- ✅ Smart pickers with context filtering
- ✅ Commands default to context when applicable
- ✅ Project names in task listings (instead of IDs)
- ✅ Bottom toolbar (task counts + rotating tips)
- ✅ Right prompt (context-aware task count)
- ✅ Clear command (clean up cluttered screens)
- ✅ Improved spacing (whitespace between command outputs)
- ⏳ Enhanced autocomplete (planned)
- ⏳ Better output formatting - relative dates, status indicators (planned)
- ⏳ Undo support (planned)

---

## 🚀 Recent Additions (This Session)

### Persistent Context System ⭐ **NEW**
- **Context filtering**: Set current working project and scope
- **Dynamic prompt**: `barely:[Work | today]>` shows active context
- **Smart defaults**: Commands automatically use context
  - `add` creates tasks in current project
  - `ls`, `today`, `week`, `backlog` filter by context
  - Flags can still override context when needed
- **Context commands**:
  - `use <project>` - Set current working project
  - `scope <scope>` - Set current scope filter
  - `use none` / `scope all` - Clear context
- **Session-scoped**: Context resets on REPL restart (by design)

### Smart Interactive Pickers ⭐ **NEW**
- **Context-aware task selection**: Pickers filter by current context
- **Inline numbered lists**: Simple, non-intrusive - stays in REPL flow
- **Bulk operations**: Use commas to select multiple (e.g., "1,3,5")
- **Works with all task commands**:
  - `done` - Shows picker for todo tasks (supports bulk)
  - `rm` - Shows picker for all tasks (supports bulk)
  - `edit <title>` - Shows picker, updates selected task (single only)
  - `mv <column>` - Shows picker, moves selected task(s) (supports bulk)
  - `pull <scope>` - Shows picker, pulls selected task(s) (supports bulk)
- **Solves the hundreds-of-tasks problem**: Only shows relevant tasks (up to 20)
- **Example workflow**:
  ```
  barely:[Work]> scope today
  barely:[Work | today]> done
  # Shows numbered list of Work tasks in today scope
  # Enter "1,3,5" to mark multiple as done, or press Enter to cancel
  ```

### ASCII Animations ⭐ **NEW**
- **Multi-line canvas animations**: 16x9 character canvas with actual visual effects
- **Firework explosion** (done): Rocket (^) launches from bottom, rises with trail, reaches peak (o), explodes in expanding starburst with ✓ at center - 16 frames
- **Sparkle burst** (add/done variant): Dot grows to star, checkmark appears at center, particles radiate outward in waves - 11 frames
- **Poof effect** (delete): Block (█) dissolves through shading (▓→▒) into dispersing smoke particles
- **Whoosh movement** (pull): Object slides across screen with motion trail
- **Frame-by-frame rendering**: ANSI terminal codes (\033[9A) move cursor up to redraw same area
- **Random variety**: Multiple animation variants per action type
- **Observable duration**: ~2.4 seconds for done (was 0.6s), 0.15s per frame (was 0.08s)
- **Auto-cleanup**: Canvas clears itself after animation completes
- **Bulk operations**: Still use text celebrations like "🚀 *rapid* 🚀 Completed 5 tasks!"
- **Implementation**: Canvas system with `_create_canvas()`, `_set_pixel()`, `_play_canvas_animation()`
- **Detailed & satisfying**: Doubled duration makes animations truly observable and rewarding

### Improved Output Formatting ⭐ **NEW**
- **Project names instead of IDs**: Task tables now show "Work" instead of "1"
- **Efficient caching**: Looks up project names once per display
- **Graceful fallback**: Shows ID if project not found, "-" for no project
- **Better scanning**: Easier to identify task context at a glance
- **Implementation**: `service.get_project()` + display-time cache

### Default REPL Launch
- Running `barely` without arguments now launches the REPL
- Updated help text to reflect this
- REPL is now the primary interface

### Flag and Filter Fixes
- ✅ Fixed --project filtering (now case-insensitive)
- ✅ Removed invalid --json/--raw flags from REPL autocomplete
- ✅ Added --project support to REPL ls command
- ✅ CLI scope commands properly support --json and --raw
- ✅ All flag autocomplete is now command-specific

### Database Migration
- Created and ran migration to add scope column
- All existing tasks migrated to backlog scope
- Migration script available: `run_migration.py`

---

## 📊 Current Capabilities

### What You Can Do Right Now

**Task Management**:
```bash
barely                          # Launch REPL (default)
barely add "Task title"         # Create task in backlog
barely ls                       # List all tasks
barely ls --status todo         # Filter by status
barely ls --project Work        # Filter by project (case-insensitive)
barely done 1,2,3              # Complete multiple tasks
barely rm 5,6,7                # Delete multiple tasks
barely edit 42 "New title"     # Update task title
```

**Pull-Based Workflow**:
```bash
barely backlog                  # View all backlog tasks (50 in your DB)
barely week                     # View this week's commitments
barely today                    # View today's focus list
barely pull 2,4,5 today        # Pull tasks into today
barely pull 7 week             # Pull task into week
barely pull 8 backlog          # Defer task back to backlog
```

**Project Organization**:
```bash
barely project add "Work"       # Create project
barely project ls               # List projects
barely project rm 2,3          # Delete multiple projects
barely mv 5 "In Progress"      # Move task to column
```

**Persistent Context (REPL Only)**:
```bash
barely> use Work                # Set context to Work project
barely:[Work]> add Fix bug      # Creates task in Work automatically
barely:[Work]> scope today      # Filter to today's tasks
barely:[Work | today]> ls       # Shows only Work tasks in today scope
barely:[Work | today]> done     # Picker shows only relevant tasks
barely:[Work | today]> use none # Clear project context
barely:[today]> scope all       # Clear scope filter
barely> ...                     # Back to normal prompt
```

**Smart Pickers (REPL Only)**:
```bash
barely> use Work
barely:[Work]> scope today
barely:[Work | today]> done
# Numbered list appears showing only Work tasks in today scope
# Enter "1" for single, "1,3,5" for multiple, or press Enter to cancel
```

**Traditional REPL Mode** (still works):
```bash
barely> add Buy groceries
barely> ls --project Work
barely> today
barely> pull 1,2,3 today
barely> done 1
barely> help
```

---

## 🔧 Technical Architecture

### Layers
```
REPL/CLI (UI)
    ↓
Service Layer (Business Logic)
    ↓
Repository Layer (Data Access)
    ↓
SQLite Database
```

### Key Files
- **Database**: `~/.barely/barely.db` (SQLite)
- **Schema**: `db/schema.sql`
- **Models**: `barely/core/models.py` (Task, Project, Column)
- **Repository**: `barely/core/repository.py` (CRUD operations)
- **Service**: `barely/core/service.py` (Business logic)
- **CLI**: `barely/cli/main.py` (Typer commands)
- **REPL**: `barely/repl/main.py` (prompt-toolkit)
- **Autocomplete**: `barely/repl/completer.py`

### Testing
- **Test Coverage**: 7 test suites, 110+ tests
  - `test_phase1.py` - Foundation
  - `test_phase2.py` - Service layer
  - `test_phase3.py` - CLI commands
  - `test_phase4.py` - REPL functionality
  - `test_phase5.py` - Projects (41 tests)
  - `test_phase6.py` - Pull workflow (40 tests)
  - `test_completer.py` - Autocomplete
  - `test_comma_separated.py` - Bulk operations
  - `test_flag_fixes.py` - Flag handling (4 tests)
  - `test_default_repl.py` - Default behavior
  - `test_context_and_pickers.py` - Context & pickers (5 tests) ⭐ NEW

---

## 📝 Your Current Data

From your database (`~/.barely/barely.db`):
- **50 tasks** (all now in backlog scope after migration)
- **12 projects** (including TestProject)
- **3 tasks in today scope** (tasks 2, 4, 5)
- **47 tasks in backlog scope**
- **0 tasks in week scope**

---

## 🎯 What's Next: Phase 7 - REPL Polish (In Progress)

Phase 7 focuses on making the REPL feel great. **Significant progress made this session!**

### Completed This Session ✅
- [x] **Persistent context system**
  - Set current working project with `use <project>`
  - Set current scope filter with `scope <scope>`
  - Dynamic prompt shows active context
  - All commands respect context automatically

- [x] **Smart interactive pickers**
  - Context-aware task selection
  - Keyboard-driven navigation
  - Works with `done`, `rm`, `edit`, `mv`, `pull` commands
  - Solves hundreds-of-tasks problem with filtering

- [x] **Updated help documentation**
  - Documents picker usage
  - Shows context workflow examples

### Remaining Tasks
- [ ] Enhanced autocomplete
  - Project names from database (dynamic)
  - Column names from database (dynamic)
  - Task IDs for quick completion

- [ ] Better output formatting
  - Improved table layouts
  - Relative dates ("2 hours ago")
  - Status indicators
  - Project names in task listings (currently shows IDs)

- [ ] REPL helpers
  - `clear` command
  - Status bar showing context (partially done via prompt)

- [ ] Quality of life
  - Undo last operation
  - Better error messages
  - Keyboard shortcuts

### Questions to Consider

1. **What feels clunky in the REPL right now?**
   - Are there workflows that require too many steps?
   - Is autocomplete helpful enough?
   - Is output easy to scan?

2. **What would make daily use better?**
   - Do you find yourself typing the same things repeatedly?
   - Are there common mistakes that could be prevented?
   - What feels slow or tedious?

3. **Should we tackle Phase 7, or is there something else?**
   - Phase 8 is Blitz Mode (focused task completion)
   - Phase 9 is extras (priorities, recurring tasks, etc.)
   - Or address specific pain points first?

---

## 💭 Design Philosophy Reminder

From CLAUDE.md:
- **REPL-first**: Interactive shell is primary interface
- **Pull-based**: You control when tasks move through scopes
- **Minimal**: No heavy automation or "smart" systems
- **Local-first**: SQLite, no cloud dependencies
- **Fast feedback**: Everything should feel snappy

**Core tenet**: "When in doubt, build the simplest version first."

---

## 🐛 Known Issues / Considerations

None critical! The system is working very well. Some observations:

1. **Display could be richer**
   - ✅ ~~Task tables show project IDs instead of names~~ **FIXED** - now shows names
   - Relative time display would be nice ("3 days ago")
   - Could show task descriptions in listings

2. **Autocomplete could be smarter** ⚠️ Still needed
   - Currently suggests commands and flags
   - Could suggest project names, column names from DB
   - Could suggest task IDs for completion

3. **Error handling is functional but could be friendlier**
   - Current errors are clear but technical
   - Could add suggestions ("Did you mean X?")

4. **No undo functionality** ⚠️ Would be valuable
   - Easy to accidentally delete or complete wrong task
   - Simple undo would be valuable
   - **Note**: Pickers help reduce mistakes by showing what you're selecting

5. **Blitz mode not yet implemented**
   - This was in the original vision
   - Focused task-completion mode within REPL
   - Could be very useful for daily work

6. **Picker limitations** ⚠️ By design
   - Limited to 20 tasks for readability
   - This is intentional - use context filtering to narrow down first

---

## 📈 Statistics

**Code Base**:
- ~3,800 lines of Python (up from ~3,500)
- 22+ commands (CLI + REPL) - added `use` and `scope`
- 6.5 phases completed (Phase 7 in progress)
- 110+ tests passing (up from 100+)
- 7 test suites

**Session Summary**:
- ✅ Implemented Phase 6 pull-based workflow
- ✅ Fixed project filtering and flag handling
- ✅ Created migration system
- ✅ Default REPL launch behavior
- ✅ **Persistent context system** (project + scope) ⭐ NEW
- ✅ **Smart interactive pickers** with context filtering ⭐ NEW
- ✅ **Bulk operations in pickers** - comma-separated selection ⭐ NEW
- ✅ **Subtle inline picker UX** - no fullscreen takeover ⭐ NEW
- ✅ **ASCII animations** - delightful feedback for operations ⭐ NEW
- ✅ **Improved output formatting** - project names instead of IDs ⭐ NEW
- ✅ Updated help documentation
- ✅ Comprehensive test coverage (5 new tests)

---

## 🎉 What's Working Really Well

1. **Layered architecture** - Clean separation makes changes easy
2. **Pull-based workflow** - Aligns with actual work patterns
3. **REPL experience** - Fast, responsive, feels good
4. **Persistent context** ⭐ NEW - Solves the hundreds-of-tasks problem
5. **Smart pickers** ⭐ NEW - Simple numbered lists, context-aware, stays inline
6. **ASCII animations** ⭐ NEW - Makes operations feel alive without being overwhelming
7. **Improved output** ⭐ NEW - Project names show clearly, not just IDs
8. **Test coverage** - High confidence in changes (110+ tests)
9. **Documentation** - CLAUDE.md keeps principles clear
10. **Bulk operations** - Comma-separated IDs are super convenient

---

## 💡 Suggestions for Next Steps

**Option A: Continue Phase 7 (REPL improvements)**
- ✅ ~~Add persistent context~~ DONE
- ✅ ~~Add inline pickers~~ DONE
- ✅ ~~Improve table formatting (show project names, not IDs)~~ DONE
- ⏳ Make autocomplete dynamic (suggest actual project names)
- ⏳ Add undo support
- ⏳ Better output formatting (relative dates)

**Option B: Jump to Phase 8 (Blitz Mode)**
- Focused task completion mode
- Show one task at a time with timer
- Keybindings for quick actions (d=done, s=skip, q=quit)
- Great for getting through today's list
- **Note**: With pickers and context, this might be less critical now

**Option C: Try it out in real usage**
- The REPL now has powerful context + picker workflow
- Use it for a day to see what still feels clunky
- Come back with real usage feedback
- **Example workflow**:
  1. `use Work` → `scope today`
  2. `done` (picker shows only Work tasks in today)
  3. Repeat until done

**My recommendation**: The REPL just got a major upgrade! Try using the context + picker workflow for real work. The combination of `use`/`scope` commands with smart pickers should make managing hundreds of tasks feel effortless. Come back with feedback on what still needs polish.

---

### END OF FILE
