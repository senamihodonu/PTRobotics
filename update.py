import sqlite3

DB_FILE = "print_data.db"

def remove_unwanted_columns():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Step 1: Rename the original table
        cursor.execute("ALTER TABLE prints RENAME TO prints_old")

        # Step 2: Create a new table without the columns you want to remove
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
                width REAL DEFAULT 0.0
            )
        ''')

        # Step 3: Copy data from the old table to the new one
        cursor.execute('''
            INSERT INTO prints (
                id, group_tag, print_tag, image_tag1, image_tag2,
                humidity, temperature, print_speed, layer_height, pressure, width
            )
            SELECT
                id, group_tag, print_tag, image_tag1, image_tag2,
                humidity, temperature, print_speed, layer_height, pressure, width
            FROM prints_old
        ''')

        # Step 4: Drop the old table
        cursor.execute("DROP TABLE prints_old")

        conn.commit()
        print("Successfully removed 'image_tag3' and 'comments' columns from the database.")

# Run it once
remove_unwanted_columns()
