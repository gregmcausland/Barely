-- Barely Database Schema
-- SQLite database for local-first task management

-- Projects: Top-level organization for tasks
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Columns: Global workflow stages (Todo, In Progress, Done, etc.)
-- Shared across all projects for consistency
CREATE TABLE IF NOT EXISTS columns (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    position INTEGER NOT NULL DEFAULT 0
);

-- Tasks: The core entity
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    column_id INTEGER NOT NULL REFERENCES columns(id),
    status TEXT CHECK(status IN ('todo', 'done', 'archived')) DEFAULT 'todo',
    scope TEXT CHECK(scope IN ('backlog', 'week', 'today')) DEFAULT 'backlog',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_column ON tasks(column_id);
CREATE INDEX IF NOT EXISTS idx_tasks_scope ON tasks(scope);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);

-- Default columns for initial setup
-- Only insert if columns table is empty (first run)
INSERT OR IGNORE INTO columns (id, name, position) VALUES
    (1, 'Todo', 1),
    (2, 'In Progress', 2),
    (3, 'Done', 3);
