import sqlite3
import csv
import os

DB_FILE = "vision.db"

# Define column order once to reuse throughout
COLUMNS = [
    "id", "group_tag", "print_tag", "image_tag1", "image_tag2",
    "vision_capture", "humidity", "temperature", "print_speed",
    "layer_width", "layer_height", "nozzle_height"
]

def create_database():
    """Create the database and 'prints' table if it doesn't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS prints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_tag TEXT,
                print_tag TEXT UNIQUE,
                image_tag1 TEXT,
                image_tag2 TEXT,
                vision_capture TEXT,
                humidity REAL DEFAULT 0.0,
                temperature REAL DEFAULT 0.0,
                print_speed REAL DEFAULT 0.0,
                layer_width REAL DEFAULT 0.0,
                layer_height REAL DEFAULT 0.0,
                nozzle_height REAL DEFAULT 0.0
            )
        ''')
        conn.commit()

def insert_print_data(group_tag, print_tag, image_tag1, image_tag2,
                      vision_capture, humidity, temperature, print_speed, layer_width, 
                      layer_height, nozzle_height):
    """Insert a new print entry into the database."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                INSERT INTO prints (
                    group_tag, print_tag, image_tag1, image_tag2,
                    vision_capture, humidity, temperature, print_speed,
                    layer_width, layer_height, nozzle_height
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                group_tag, print_tag,
                image_tag1 or 'None', image_tag2 or 'None',
                vision_capture or 'None',
                humidity or 0.0, temperature or 0.0,
                print_speed or 0.0, layer_width or 0.0,
                layer_height or 0.0, nozzle_height or 0.0
            ))
            conn.commit()
    except sqlite3.IntegrityError:
        print(f"Error: Print tag '{print_tag}' already exists.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")

def fetch_all_data():
    """Fetch and display all print data from the database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {', '.join(COLUMNS)} FROM prints")
        rows = cursor.fetchall()

    if rows:
        print("\n--- All Data in Database ---")
        print(", ".join(COLUMNS))
        for row in rows:
            print(row)
    else:
        print("No data found in the database.")

def export_by_group_tag(group_tag):
    """Export data for a specific group_tag to a CSV file."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {', '.join(COLUMNS)} FROM prints WHERE group_tag = ?", (group_tag,))
        rows = cursor.fetchall()

    if not rows:
        print(f"No data found for group_tag: {group_tag}")
        return

    filename = f"{group_tag}_export.csv"
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    print(f"Data for group_tag '{group_tag}' exported to {filename}")

def export_session_data(group_tag, session_folder):
    """Export session data for a given group_tag to a CSV in a specified folder."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {', '.join(COLUMNS)} FROM prints WHERE group_tag = ?", (group_tag,))
        rows = cursor.fetchall()

    if not rows:
        print(f"No data found for session: {group_tag}")
        return

    session_csv_path = os.path.join(session_folder, "session_data.csv")
    with open(session_csv_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    print(f"Session data exported to: {session_csv_path}")

def get_data_by_group_tag(group_tag):
    """Retrieve records by group_tag."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prints WHERE group_tag = ?", (group_tag,))
        return cursor.fetchall()

def delete_print_data(print_tag):
    """Delete a single print record by its print_tag."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prints WHERE print_tag = ?", (print_tag,))
        conn.commit()
        print(f"Deleted record with print_tag: {print_tag}" if cursor.rowcount else f"No record found with print_tag: {print_tag}")

def delete_by_group_tag(group_tag):
    """Delete all records associated with a specific group_tag."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prints WHERE group_tag = ?", (group_tag,))
        conn.commit()
        print(f"Deleted all records with group_tag: {group_tag}" if cursor.rowcount else "No records found with that group_tag.")

def delete_all_data():
    """Delete all records in the database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM prints")
        conn.commit()
    print("All data deleted from the database.")

def update_print_data(print_tag, **fields):
    """Update fields of a record identified by print_tag."""
    if not fields:
        print("No fields provided to update.")
        return

    set_clause = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [print_tag]

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            UPDATE prints
            SET {set_clause}
            WHERE print_tag = ?
        ''', values)
        conn.commit()

        if cursor.rowcount:
            print(f"Successfully updated print_tag: {print_tag}")
        else:
            print(f"No record found with print_tag: {print_tag}")

def main():
    create_database()

    while True:
        print("\n--- Database Processing Options ---")
        print("1. View all data")
        print("2. Export data by group_tag")
        print("3. Delete record by print_tag")
        print("4. Delete records by group_tag")
        print("5. Delete all data")
        print("6. Update print data by print_tag")
        print("7. Exit")

        choice = input("Enter your choice (1/2/3/4/5/6/7): ").strip()

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
            print_tag = input("Enter the print_tag to update: ").strip()
            field = input("Enter the field name to update: ").strip()
            value = input("Enter the new value: ").strip()

            numeric_fields = {
                "humidity", "temperature", "print_speed",
                "nozzle_height", "layer_width", "layer_height"
            }

            if field in numeric_fields:
                try:
                    value = float(value)
                except ValueError:
                    print("Invalid numeric value.")
                    continue

            update_print_data(print_tag, **{field: value})
        elif choice == '7':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please select a valid option.")

if __name__ == "__main__":
    main()
