import sqlite3
import shutil

DB_FILE = "print_data.db"
BACKUP_FILE = "print_data_backup.db"

def backup_database():
    shutil.copy(DB_FILE, BACKUP_FILE)
    print(f"Backup created at {BACKUP_FILE}")

def drop_comments_column():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Define the target schema without 'comments'
        new_columns_definitions = [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "group_tag TEXT",
            "print_tag TEXT UNIQUE",
            "image_tag1 TEXT",
            "image_tag2 TEXT",
            "image_tag3 TEXT",
            "humidity REAL DEFAULT 0.0",
            "temperature REAL DEFAULT 0.0",
            "print_speed REAL DEFAULT 0.0",
            "layer_height REAL DEFAULT 0.0",
            "pressure REAL DEFAULT 0.0",
            "width REAL DEFAULT 0.0"
        ]

        # Define the list of columns to transfer (excluding 'comments')
        columns_to_copy = [
            "id",
            "group_tag",
            "print_tag",
            "image_tag1",
            "image_tag2",
            "image_tag3",
            "humidity",
            "temperature",
            "print_speed",
            "layer_height",
            "pressure",
            "width"
        ]

        # Rename the original table
        cursor.execute("ALTER TABLE prints RENAME TO prints_old")

        # Create the new table
        create_stmt = f"CREATE TABLE prints ({', '.join(new_columns_definitions)})"
        cursor.execute(create_stmt)

        # Copy data from the old table to the new table
        column_str = ", ".join(columns_to_copy)
        cursor.execute(f"INSERT INTO prints ({column_str}) SELECT {column_str} FROM prints_old")

        # Drop the old table
        cursor.execute("DROP TABLE prints_old")
        conn.commit()
        print("Migration successful: 'comments' column removed and schema aligned.")

def main():
    backup_database()
    drop_comments_column()

if __name__ == "__main__":
    main()
