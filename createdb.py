import sqlite3

## set out statements for db
sql_statements = [
"""CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY,
    alert_header text NOT NULL,
    alert_description text NOT NULL,
    time_stamp DATE,
);"""

]


try:
    with sqlite3.connect("servicealerts.db") as conn:
        print(f"Sucuessfully created SQLite database with SQLite version {sqlite3.sqlite_version}")
        cursor = conn.cursor()  # Get a cursor from the connection
        for statement in sql_statements:
            cursor.execute(statement)
            conn.commit()
        print("Tables created successfully")

except sqlite3.OperationalError as e:
    print("Failed to open database", e)


except sqlite3.OperationalError as err:
    print("Failed to create table:", err)

quit()