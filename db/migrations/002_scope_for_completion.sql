-- Migration: Use scope='archived' for completed tasks instead of status/column_id
-- This makes completion consistent with the pull-based workflow
-- Tasks can be reactivated by pulling them back to backlog/week/today

-- Step 1: Update scope constraint to include 'archived'
-- SQLite doesn't support ALTER TABLE CHECK constraint modification directly,
-- so we need to recreate the constraint by:
-- 1. Create new table with updated constraint
-- 2. Copy data
-- 3. Drop old table
-- 4. Rename new table

-- For safety, we'll update existing completed tasks first, then handle constraint
-- Note: SQLite doesn't easily modify CHECK constraints, so we'll rely on the
-- application layer to enforce this and update the schema for new databases

-- Step 2: Migrate existing completed tasks to scope='archived'
-- Tasks that are done (column_id=3 or status='done') should be moved to archived scope
UPDATE tasks 
SET scope = 'archived' 
WHERE (column_id = 3 OR status = 'done') AND scope != 'archived';

-- Step 3: Set completed_at timestamp for archived tasks that don't have it
-- Use updated_at as fallback, or current timestamp if neither exists
UPDATE tasks 
SET completed_at = COALESCE(completed_at, updated_at, datetime('now'))
WHERE scope = 'archived' AND completed_at IS NULL;

