"""
Apply Phase 6 migration to add scope column to existing database.
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

def run_migration():
    """Apply the scope migration to the database."""

    # Check if database exists
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        print("No migration needed - new database will be created with scope column.")
        return

    print(f"Applying migration to database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if scope column already exists
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'scope' in columns:
            print("✓ Scope column already exists - no migration needed")
            return

        print("Adding scope column...")

        # Add scope column
        cursor.execute("""
            ALTER TABLE tasks
            ADD COLUMN scope TEXT
            CHECK(scope IN ('backlog', 'week', 'today'))
            DEFAULT 'backlog'
        """)

        # Create index
        print("Creating scope index...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_scope ON tasks(scope)")

        # Update existing tasks
        print("Setting scope='backlog' for existing tasks...")
        cursor.execute("UPDATE tasks SET scope = 'backlog' WHERE scope IS NULL")

        conn.commit()
        print("✓ Migration completed successfully!")

        # Show summary
        cursor.execute("SELECT COUNT(*) FROM tasks")
        task_count = cursor.fetchone()[0]
        print(f"✓ {task_count} task(s) now have scope='backlog'")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
