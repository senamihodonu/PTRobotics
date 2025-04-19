import sqlite3

DB_FILE = "print_data.db"

def migrate_table_schema():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Step 1: Rename old table
        cursor.execute("ALTER TABLE prints RENAME TO prints_old")

        # Step 2: Create new table with corrected column order
        cursor.execute('''
            CREATE TABLE prints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_tag TEXT,
                print_tag TEXT UNIQUE,
                image_tag1 TEXT,
                image_tag2 TEXT,
                humidity REAL DEFAULT 0.0,
                temperature REAL DEFAULT 0.0,
                print_speed REAL DEFAULT 0.0,
                layer_height REAL DEFAULT 0.0,
                pressure REAL DEFAULT 0.0,
                width REAL DEFAULT 0.0,
                image_tag3 TEXT,
                comments TEXT DEFAULT ''
            )
        ''')

        # Step 3: Copy data into new table (matching the new column order)
        cursor.execute('''
            INSERT INTO prints (
                id, group_tag, print_tag, image_tag1, image_tag2,
                humidity, temperature, print_speed, layer_height,
                pressure, width, image_tag3, comments
            )
            SELECT 
                id, group_tag, print_tag, image_tag1, image_tag2,
                humidity, temperature, print_speed, layer_height,
                pressure, width, image_tag3, comments
            FROM prints_old
        ''')

        # Step 4: Drop old table
        cursor.execute("DROP TABLE prints_old")

        conn.commit()
        print("✅ Table migration successful! Columns reordered and data preserved.")

if __name__ == "__main__":
    migrate_table_schema()
