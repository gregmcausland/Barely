# Phase 7 Completion Plan

**Status**: In Progress (90% complete)  
**Goal**: Complete remaining Phase 7 polish items to make REPL feel great for daily use

---

## Current State Assessment

### ✅ Already Complete (Phase 7)

- [x] **Persistent context system** - `use` and `scope` commands working
- [x] **Smart pickers** - Context-aware task selection implemented
- [x] **Output formatting** - Rich tables with color coding by scope/status
- [x] **Bottom toolbar** - Task counts + rotating tips
- [x] **Right prompt** - Context-aware task count
- [x] **Clear command** - Screen clearing implemented
- [x] **Help command** - Comprehensive help documentation
- [x] **Project names in output** - Shows names instead of IDs
- [x] **Animations** - ASCII animations for operations
- [x] **Task descriptions** - `desc` command to edit, `show` to view

### ✅ Dynamic Autocomplete (Mostly Complete)

- [x] **Project names** - Dynamic from database (for `use`, `assign` commands)
- [x] **Column names** - Dynamic from database (for `mv` command)
- [x] **Task IDs** - Dynamic with labels (for `done`, `rm`, `edit`, etc.)
- [x] **Pull scopes** - Static list (`today`, `week`, `backlog`)
- [ ] **Scope command** - Missing autocomplete for `scope` command itself

### ⏳ Remaining Tasks

#### 1. Scope Command Autocomplete

**Priority**: High  
**Effort**: Low (30 minutes)

**What's Missing**:

- Typing `scope ` should suggest: `today`, `week`, `backlog`, `all`

**Implementation**:

- Add case in `barely/repl/completer.py` for `scope` command
- Use same scopes as `pull` command: `["backlog", "week", "today"]`
- Also suggest `"all"`, `"none"`, `"clear"` (clear options)

**Files to Modify**:

- `barely/repl/completer.py` - Add `_complete_scope_values()` method
- Add case in `get_completions()` method

**Testing**:

- Test autocomplete suggests scopes after `scope `
- Test autocomplete filters based on partial input (e.g., `scope t` → `today`)

---

#### 2. Relative Date Display

**Priority**: Medium  
**Effort**: Medium (2-3 hours)

**What's Missing**:

- Currently shows raw timestamps: `2025-01-26T14:30:00`
- Should show: `"2 hours ago"`, `"tomorrow"`, `"3 days ago"`, `"Jan 15"`

**Implementation Plan**:

1. Create utility function in `barely/repl/style.py` or new `barely/repl/formatting.py`:

   ```python
   def format_relative_date(iso_string: str) -> str:
       """Convert ISO timestamp to relative time string."""
       # Parse ISO string
       # Calculate difference from now
       # Return human-readable string
   ```

2. Update display functions:

   - `display_tasks_table()` - Show relative dates in table
   - `handle_show_command()` - Show relative dates in task details
   - CLI `show` command - Show relative dates

3. Handle edge cases:
   - Future dates (e.g., "tomorrow", "in 2 days")
   - Very old dates (e.g., "2 months ago", "Jan 2024")
   - Same day (e.g., "2 hours ago", "just now")
   - Today/tomorrow (e.g., "today", "tomorrow")

**Files to Modify**:

- Create `barely/repl/formatting.py` (new file)
- Update `barely/repl/main.py` - `display_tasks_table()`, `handle_show_command()`
- Update `barely/cli/main.py` - `show()` command

**Dependencies**:

- `datetime` module (stdlib)
- Consider `humanize` library OR custom implementation

**Testing**:

- Test various time differences (seconds, minutes, hours, days, months)
- Test edge cases (today, tomorrow, same time, very old)
- Test formatting consistency across CLI and REPL

---

#### 3. Undo Support

**Priority**: Medium  
**Effort**: Medium-High (3-4 hours)

**What's Missing**:

- No way to undo last operation
- Easy to accidentally delete or complete wrong task

**Implementation Plan**:

1. Create undo history tracker (`barely/repl/undo.py`):

   ```python
   @dataclass
   class UndoOperation:
       operation: str  # 'create', 'delete', 'complete', 'update_title', 'pull', etc.
       original_data: dict  # Snapshot of task before operation
       new_data: dict  # Snapshot of task after operation
       timestamp: str
   ```

2. Track operations in REPL handlers:

   - `handle_add_command()` - Track creation
   - `handle_done_command()` - Track completion (store original status)
   - `handle_rm_command()` - Track deletion (store full task)
   - `handle_edit_command()` - Track title update
   - `handle_pull_command()` - Track scope changes
   - `handle_mv_command()` - Track column moves

3. Implement `handle_undo_command()`:

   - Check if undo history exists
   - Reverse last operation based on type
   - Support undo for: delete, complete, edit, pull, mv
   - Show confirmation/what was undone

4. Storage:
   - In-memory list (last 10 operations)
   - Session-scoped (reset on REPL restart)

**Files to Create**:

- `barely/repl/undo.py` - Undo tracking and reversal logic

**Files to Modify**:

- `barely/repl/main.py` - Add undo tracking to command handlers
- `barely/repl/main.py` - Add `handle_undo_command()` handler
- `barely/repl/completer.py` - Add `undo` to commands list

**Limitations** (by design):

- Only undo last operation
- No undo for bulk operations (too complex)
- No undo for project operations (can be recreated)
- Session-scoped only (no persistence)

**Testing**:

- Test undo for each operation type
- Test undo when no history exists
- Test undo after multiple operations (should undo last only)
- Test undo doesn't break context/pickers

---

#### 4. Task Descriptions in Listings (Optional Enhancement)

**Priority**: Low  
**Effort**: Low-Medium (1-2 hours)

**Current State**:

- Descriptions exist in database
- `desc` command can edit descriptions
- `show` command displays full description
- But descriptions not shown in `ls`/table output

**Proposal**:

- Option 1: Add truncated description column to tables (if description exists)
- Option 2: Add `--full` flag to `ls` to show descriptions
- Option 3: Show description in expanded view (separate command)

**Recommendation**: Skip for Phase 7, add to Phase 9 if needed. Descriptions are already accessible via `show` command.

---

## Implementation Order

**Recommended Sequence**:

1. ✅ **Scope autocomplete** (Quick win, 30 min)
2. ✅ **Relative dates** (Medium effort, high UX impact)
3. ✅ **Undo support** (Medium effort, safety feature)
4. ⏸️ **Task descriptions in listings** (Defer to Phase 9)

---

## Testing Strategy

For each feature:

1. **Unit tests** - Test formatting/undo logic functions
2. **Integration tests** - Test in REPL context
3. **Manual testing** - Interactive REPL testing
4. **Edge cases** - Error handling, empty states

**Test Files**:

- `test_phase7_autocomplete.py` - Scope autocomplete tests
- `test_phase7_formatting.py` - Relative date formatting tests
- `test_phase7_undo.py` - Undo functionality tests

---

## Documentation Updates

After completion:

1. Update `ROADMAP.md` - Mark Phase 7 tasks as complete
2. Update `STATUS.md` - Document Phase 7 completion
3. Update `README.md` - Update version if needed
4. Update help text - Add `undo` command to help

---

## Definition of Done

Phase 7 is complete when:

- [x] Scope command has autocomplete
- [x] Relative dates display in task listings and details
- [x] Undo command works for common operations
- [x] All tests pass
- [x] Documentation updated
- [x] REPL feels polished and responsive

---

## Notes

- **Keep it simple**: Focus on most impactful features first
- **User testing**: Consider using Phase 7 features for a day before adding more
- **Phase 8 already complete**: Blitz mode is done, so Phase 7 is the final polish
- **Phase 9 waiting**: Extras can wait until Phase 7 is solid

---

## Estimated Time to Complete

- Scope autocomplete: **30 minutes**
- Relative dates: **2-3 hours**
- Undo support: **3-4 hours**
- Testing: **1-2 hours**
- Documentation: **30 minutes**

**Total**: ~8-10 hours of focused work

---

**Last Updated**: 2025-01-26  
**Status**: Planning complete, ready for implementation
