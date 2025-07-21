#!/usr/bin/env python3
"""Database migration script to add enhanced logging columns."""

import sqlite3

def migrate_database():
    """Migrate the database to add enhanced logging columns."""
    print('Starting database migration...')
    conn = sqlite3.connect('RCI_local.db')
    cursor = conn.cursor()

    # Check current schema
    cursor.execute('PRAGMA table_info(RCI_debug_log)')
    current_columns = [row[1] for row in cursor.fetchall()]
    print(f'Current columns: {current_columns}')

    # Add missing columns if they don't exist
    missing_columns = []
    expected_columns = ['level', 'category', 'stack_trace']

    for col in expected_columns:
        if col not in current_columns:
            missing_columns.append(col)

    if missing_columns:
        print(f'Adding missing columns: {missing_columns}')
        for col in missing_columns:
            try:
                if col == 'level':
                    cursor.execute('ALTER TABLE RCI_debug_log ADD COLUMN level TEXT DEFAULT "INFO"')
                elif col == 'category':
                    cursor.execute('ALTER TABLE RCI_debug_log ADD COLUMN category TEXT DEFAULT "GENERAL"')
                elif col == 'stack_trace':
                    cursor.execute('ALTER TABLE RCI_debug_log ADD COLUMN stack_trace TEXT')
                print(f'  Added column: {col}')
            except Exception as e:
                print(f'  Error adding {col}: {e}')
        
        conn.commit()
        print('Migration completed')
    else:
        print('No migration needed - all columns present')

    # Verify final schema
    cursor.execute('PRAGMA table_info(RCI_debug_log)')
    final_columns = [row for row in cursor.fetchall()]
    print(f'Final schema: {final_columns}')

    conn.close()

if __name__ == "__main__":
    migrate_database()
