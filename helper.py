import sqlite3

DBNAME = 'monitor.db'

def test_sqlite_conn():
    try:
        # Attempts to create a connection to an in-memory SQLite database.
        conn = sqlite3.connect(':memory:')
        print("SQLite is LIVE on your system")
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error: {e}")

def connect_sqlite_db(db_name=DBNAME):
    if test_sqlite_conn():
        # if it does not exist, will create
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        return cursor


if __name__ == '__main__':
   connect_sqlite_db()

