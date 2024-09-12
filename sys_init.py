import sqlite3

from nbclient.client import timestamp

from helper import connect_sqlite_db
from definitions import EventType, event_stream, Constraint, Rule, EventAtom, ArithmeticAtom

cursor = connect_sqlite_db()

# based on the event type objects, create the event table using sql in sqlite
def create_event_table(EventTypeList=event_stream):
    # constructing the attributes' sql
    attributes_sql = ''

    # all_attribute_names = set()
    all_attributes = {}

    for et in event_stream:
        # all_attribute_names.update(et.attribute_names)
        all_attributes.update(et.attributes)

    # need to define datatype mapping? what datatype are allowed in definition?
    for attribute_name, datatype in all_attributes.items():
        attributes_sql += f'{attribute_name} {datatype},'

    create_sql = f'''
    CREATE TABLE IF NOT EXISTS events (
    event_report_time INTEGER,
    event_type_name TEXT,
    {attributes_sql}
    event_time INTEGER,
    event_id TEXT,
    PRIMARY KEY (event_id)
    )
    '''
    print(f"event table creation sql: {create_sql}")

    try:
        cursor.execute(create_sql)
    except sqlite3.Error as e:
        print(f"Error: {e}")
    return

r = Rule(rule_id=1,
         body=[EventAtom("RentBike", terms=["Bid", "Cid"], timestamp_variable="x")],
         head=[EventAtom("ReturnBike", terms=["Bid", "Cid"], timestamp_variable="y"),
               ArithmeticAtom(left_term="y", constant=-24, comparative_operator="<=", right_term="x")])

def create_body_assignment(r):
    '''
    r need to be a rule class
    '''


if __name__ == '__main__':
    create_event_table()
