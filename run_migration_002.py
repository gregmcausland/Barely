"""
Apply Migration 002: Add 'archived' to scope constraint.
This enables scope-based completion instead of status/column_id-based.
"""

import sqlite3
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Database path
DB_DIR = Path.home() / ".barely"
DB_PATH = DB_DIR / "barely.db"

def check_constraint_allows_archived(conn: sqlite3.Connection) -> bool:
    """Check if scope constraint already allows 'archived'."""
    cursor = conn.cursor()
    # Get the CREATE TABLE statement
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='tasks'")
    result = cursor.fetchone()
    if result and result[0]:
        sql = result[0]
        # Look for scope CHECK constraint that includes 'archived'
        import re
        # Find scope CHECK constraint
        scope_match = re.search(r"scope\s+TEXT\s+CHECK\(scope\s+IN\s*\(([^)]+)\)\)", sql, re.IGNORECASE)
        if scope_match:
            values = scope_match.group(1)
            return "'archived'" in values
    return False

def run_migration():
    """Apply migration 002 to update scope constraint."""
    
    # Check if database exists
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        print("No migration needed - new database will be created with updated schema.")
        return
    
    print(f"Applying Migration 002 to database: {DB_PATH}")
    print("Note: Close any running Barely instances before running this migration.")
    
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    cursor = conn.cursor()
    
    try:
        # Check if constraint already allows 'archived'
        if check_constraint_allows_archived(conn):
            print("✓ Scope constraint already includes 'archived' - no migration needed")
            return
        
        print("Recreating tasks table with updated scope constraint...")
        
        # Clean up any partial migration state
        cursor.execute("DROP TABLE IF EXISTS tasks_new")
        
        # Step 1: Create new table with updated constraint
        cursor.execute("""
            CREATE TABLE tasks_new (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                column_id INTEGER NOT NULL REFERENCES columns(id),
                status TEXT CHECK(status IN ('todo', 'done', 'archived')) DEFAULT 'todo',
                scope TEXT CHECK(scope IN ('backlog', 'week', 'today', 'archived')) DEFAULT 'backlog',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Step 2: Copy data with transformation - migrate completed tasks during copy
        print("Copying and transforming data to new table...")
        cursor.execute("""
            INSERT INTO tasks_new 
            SELECT 
                id,
                title,
                description,
                project_id,
                column_id,
                status,
                CASE 
                    WHEN column_id = 3 OR status = 'done' THEN 'archived'
                    WHEN scope IN ('backlog', 'week', 'today') THEN scope
                    ELSE 'backlog'
                END as scope,
                created_at,
                completed_at,
                updated_at
            FROM tasks
        """)
        
        # Step 3: Set completed_at for archived tasks that don't have it
        print("Setting completed_at timestamps for archived tasks...")
        cursor.execute("""
            UPDATE tasks_new 
            SET completed_at = COALESCE(completed_at, updated_at, datetime('now'))
            WHERE scope = 'archived' AND completed_at IS NULL
        """)
        
        # Step 4: Drop old table
        print("Dropping old table...")
        cursor.execute("DROP TABLE tasks")
        
        # Step 5: Rename new table
        print("Renaming new table...")
        cursor.execute("ALTER TABLE tasks_new RENAME TO tasks")
        
        # Step 6: Recreate indexes
        print("Recreating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_column ON tasks(column_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_scope ON tasks(scope)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)")
        
        conn.commit()
        print("✓ Migration 002 completed successfully!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE scope = 'archived'")
        archived_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tasks")
        total_count = cursor.fetchone()[0]
        print(f"✓ {archived_count} task(s) in archived scope")
        print(f"✓ {total_count} total task(s) migrated")
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()

