# Smart Picker Examples

The picker now supports **bulk operations** via comma-separated selection!

## Example 1: Mark Multiple Tasks as Done

```
barely:[Work | today]> done

Mark task as done
  [1] Fix critical bug (id:15, today)
  [2] Write tests (id:23, today)
  [3] Update docs (id:42, today)
  [4] Code review (id:51, today)

Select number(s) - use commas for multiple (or press Enter to cancel): 1,2,4
✓ Completed: Fix critical bug
✓ Completed: Write tests
✓ Completed: Code review
✓ Completed 3 tasks
```

## Example 2: Pull Multiple Tasks into Today

```
barely:[Work | week]> pull today

Pull task(s) into 'today'
  [1] Implement feature X (id:102, week)
  [2] Fix bug Y (id:103, week)
  [3] Review PR Z (id:104, week)
  [4] Update dependencies (id:105, week)

Select number(s) - use commas for multiple (or press Enter to cancel): 1,3
📋 Pulled task 102 into today: Implement feature X
📋 Pulled task 104 into today: Review PR Z
✓ Pulled 2 tasks into today
```

## Example 3: Delete Multiple Tasks

```
barely:[Work]> rm

Delete task
  [1] Old task 1 (id:7, backlog)
  [2] Old task 2 (id:8, backlog)
  [3] Old task 3 (id:9, backlog)
  [4] Keep this one (id:10, backlog)

Select number(s) - use commas for multiple (or press Enter to cancel): 1,2,3
✓ Deleted task 7
✓ Deleted task 8
✓ Deleted task 9
✓ Deleted 3 tasks
```

## Example 4: Move Multiple Tasks to Column

```
barely:[Work]> mv Done

Move task(s) to 'Done'
  [1] Task A (id:11, today)
  [2] Task B (id:12, today)
  [3] Task C (id:13, today)

Select number(s) - use commas for multiple (or press Enter to cancel): 1,2
→ Moved to Done: Task A
→ Moved to Done: Task B
✓ Moved 2 tasks to Done
```

## Key Features

- **Consistent with direct ID input**: Same comma-separated syntax
- **Context-aware**: Only shows tasks matching current project/scope filter
- **Bulk or single**: Use "1" for single, "1,3,5" for multiple
- **Easy to cancel**: Just press Enter with no input
- **Clear feedback**: Shows what was selected and summary for bulk ops

## Commands Supporting Bulk Selection

✅ **done** - Mark multiple tasks complete
✅ **rm** - Delete multiple tasks
✅ **mv** - Move multiple tasks to same column
✅ **pull** - Pull multiple tasks into same scope
⚠️ **edit** - Single task only (uses first if multiple selected)
