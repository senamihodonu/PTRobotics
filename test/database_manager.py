import sqlite3
import csv
import os

DB_FILE = "print_data.db"

def create_database():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_tag TEXT,
                print_tag TEXT UNIQUE,
                image_tag1 TEXT,
                image_tag2 TEXT,
                image_tag3 TEXT,
                humidity REAL DEFAULT 0.0,
                temperature REAL DEFAULT 0.0,
                print_speed REAL DEFAULT 0.0,
                layer_height REAL DEFAULT 0.0,
                pressure REAL DEFAULT 0.0,
                width REAL DEFAULT 0.0
            )
        ''')
        conn.commit()

def update_table_schema():
    """ Add missing columns if they don't exist """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE prints ADD COLUMN pressure REAL DEFAULT 0.0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE prints ADD COLUMN width REAL DEFAULT 0.0")
        except sqlite3.OperationalError:
            pass
        conn.commit()

def get_data_by_group_tag(group_tag):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prints WHERE group_tag = ?", (group_tag,))
        rows = cursor.fetchall()
        return rows

def export_session_data(group_tag, session_folder):
    """ Export all data for the current session to a CSV file in the session folder """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prints WHERE group_tag = ?", (group_tag,))
        rows = cursor.fetchall()

        if not rows:
            print(f"No data found for session: {group_tag}")
            return

        headers = [description[0] for description in cursor.description]
        session_csv_path = os.path.join(session_folder, "session_data.csv")

        with open(session_csv_path, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(rows)

        print(f"Session data exported to: {session_csv_path}")

def insert_print_data(group_tag, print_tag, image_tag1, image_tag2, image_tag3,
                      humidity, temperature, print_speed, layer_height,
                      pressure, width):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO prints (
                    group_tag, print_tag, image_tag1, image_tag2, image_tag3,
                    humidity, temperature, print_speed, layer_height,
                    pressure, width
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (group_tag, print_tag, image_tag1 or '', image_tag2 or '', image_tag3 or '',
                  humidity or 0.0, temperature or 0.0, print_speed or 0.0, layer_height or 0.0,
                  pressure or 0.0, width or 0.0))
            conn.commit()
    except sqlite3.IntegrityError:
        print(f"Error: Print tag '{print_tag}' already exists.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")

def fetch_all_data():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prints")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]

    if rows:
        print("\n--- All Data in Database ---")
        print(", ".join(columns))
        for row in rows:
            print(row)
    else:
        print("No data found in the database.")

def delete_print_data(print_tag):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prints WHERE print_tag = ?", (print_tag,))
        conn.commit()
        print(f"Deleted data with print_tag: {print_tag}" if cursor.rowcount else f"No record found with print_tag: {print_tag}")

def delete_all_data():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prints")
        conn.commit()
    print("All data deleted from the database.")

def export_by_group_tag(group_tag):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prints WHERE group_tag = ?", (group_tag,))
        rows = cursor.fetchall()

    if not rows:
        print(f"No data found for group_tag: {group_tag}")
        return

    filename = f"{group_tag}_export.csv"
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        headers = [description[0] for description in cursor.description]
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Data for group_tag '{group_tag}' exported to {filename}")

def delete_by_group_tag(group_tag):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prints WHERE group_tag = ?", (group_tag,))
        conn.commit()
        print(f"Deleted all records with group_tag: {group_tag}" if cursor.rowcount else "No records found with that group_tag.")

def main():
    create_database()
    update_table_schema()

    while True:
        print("\n--- Database Processing Options ---")
        print("1. View all data")
        print("2. Export data by group_tag")
        print("3. Delete row by print_tag")
        print("4. Delete rows by group_tag")
        print("5. Delete all data")
        print("6. Exit")

        choice = input("Enter your choice (1/2/3/4/5/6): ").strip()

        if choice == '1':
            fetch_all_data()
        elif choice == '2':
            group_tag = input("Enter the group_tag to export: ").strip()
            if group_tag:
                export_by_group_tag(group_tag)
        elif choice == '3':
            print_tag = input("Enter the print_tag to delete: ").strip()
            if print_tag:
                delete_print_data(print_tag)
        elif choice == '4':
            group_tag = input("Enter the group_tag to delete: ").strip()
            if group_tag:
                delete_by_group_tag(group_tag)
        elif choice == '5':
            delete_all_data()
        elif choice == '6':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please select a valid option.")

if __name__ == "__main__":
    main()
