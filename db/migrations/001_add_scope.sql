-- Migration: Add scope field to tasks table
-- Adds the scope field for pull-based workflow (backlog, week, today)

-- Add scope column with default value 'backlog'
ALTER TABLE tasks ADD COLUMN scope TEXT CHECK(scope IN ('backlog', 'week', 'today')) DEFAULT 'backlog';

-- Create index for scope queries
CREATE INDEX IF NOT EXISTS idx_tasks_scope ON tasks(scope);

-- Update existing tasks to have scope='backlog'
UPDATE tasks SET scope = 'backlog' WHERE scope IS NULL;
