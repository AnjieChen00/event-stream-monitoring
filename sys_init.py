import sqlite3

from attr import attributes
from nbclient.client import timestamp

from helper import connect_sqlite_db
from definitions import EventType, event_stream, Constraint, Rule, EventAtom, ArithmeticAtom

cursor = connect_sqlite_db()
all_attributes = {}
EVENT_TABLE = 'events'

# based on the event type objects, create the event table using sql in sqlite
def create_event_table(EventTypeList=event_stream):
    # constructing the attributes' sql
    attributes_sql = ''

    # all_attribute_names = set()
    global all_attributes

    for et in event_stream:
        # all_attribute_names.update(et.attribute_names)
        all_attributes.update(et.attributes)

    # need to define datatype mapping? what datatype are allowed in definition?
    for attribute_name, datatype in all_attributes.items():
        attributes_sql += f'{attribute_name} {datatype},'

    create_sql = f'''
    CREATE TABLE IF NOT EXISTS {EVENT_TABLE} (
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

# just an example to test
r = Rule(rule_id=1,
         body=[EventAtom("RentBike", terms=["Bid", "Cid"], timestamp_variable="x")],
         head=[EventAtom("RentBike", terms=["Bid", "Cid"], timestamp_variable="y"),
               ArithmeticAtom(left_term="y", constant=-24, comparative_operator="<=", right_term="x")])


def create_body_assignment(r: Rule):
    '''
    r need to be a rule class
    '''
    terms_sql = ''
    time_var_sql = ''

    all_terms = set()
    all_time_vars = set()
    for atom in r.body:
        if isinstance(atom, EventAtom):
            all_terms.update(set(atom.terms))
            all_time_vars.add(atom.timestamp_variable)

    for term in list(all_terms):
        terms_sql += f'{term} {all_attributes[term]},'
    for time_var in list(all_time_vars):
        time_var_sql += f'{time_var} INTEGER,'

    create_ba_sql = f'''
    CREATE TABLE IF NOT EXISTS body_assignment_{r.rule_id} (
    aid TEXT,
    Associated_event_ids TEXT,
    {terms_sql}
    {time_var_sql}
    gap_atoms BLOB
    match BOOLEAN DEFAULT False, 
    PRIMARY KEY (aid)
    )
    '''
    # BLOB is storing serialized python objects by pick.dumps(obj)
    print(f"BA creation sql: {create_ba_sql}")

    try:
        cursor.execute(create_ba_sql)
    except sqlite3.Error as e:
        print(f"Error: {e}")

    return

def create_head_assignment(r: Rule):
    '''
    r need to be a rule class
    '''
    terms_sql = ''
    time_var_sql = ''

    all_terms = set()
    all_time_vars = set()
    for atom in r.head:
        if isinstance(atom, EventAtom):
            all_terms.update(set(atom.terms))
            all_time_vars.add(atom.timestamp_variable)

    for term in list(all_terms):
        terms_sql += f'{term} {all_attributes[term]},'
    for time_var in list(all_time_vars):
        time_var_sql += f'{time_var} INTEGER,'

    create_ha_sql = f'''
    CREATE TABLE IF NOT EXISTS head_assignment_{r.rule_id} (
    aid TEXT,
    Associated_event_ids TEXT,
    {terms_sql}
    {time_var_sql}
    gap_atoms BLOB,
    PRIMARY KEY (aid)
    )
    '''
    # BLOB is storing serialized python objects by pick.dumps(obj)
    print(f'HA creation sql: {create_ha_sql}')

    try:
        cursor.execute(create_ha_sql)
    except sqlite3.Error as e:
        print(f"Error: {e}")

    return

c1 = Constraint(body_event_label="a1", body_event_type_name="RentBike", body_attributes={"Bid": "x", "Cid": "y"},
				min_delay=1, max_delay=None, comparative_keyword="LATER", min_count=1, max_count=1,
				head_event_label="b1", head_event_type_name="ReturnBike", head_attributes={"Bid": "x", "Cid": "y"},
				violation_handling={("TIME UNDER", ("a1", "b1")): "DELETE a1 b1",
									# ("TIME OVER", ("a1", "b1")): "DELETE a1 b1",
									("COUNT OVER", ("b1")): "DELETE b1",
									# ("COUNT UNDER", ("b1")): "WAIT"
									})
def constraint_translation(c: Constraint):
    condition = ''
    attributes_select = ''

    relation_attributes = set()
    # match body_attributes with head_attributes to find the relation attributes we are looking at
    for body_attr, body_label in c.body_attributes.items():
        for head_attr, head_label in c.head_attributes.items():
            if head_attr == body_attr and head_label == body_label:
                relation_attributes.add(body_attr)
    relation_attributes = list(relation_attributes)

    for i in range(len(relation_attributes)):
        attr = relation_attributes[i]
        condition += f'body.{attr}=head.{attr} and '
        attributes_select += f'body.{attr} as body_{attr}, head.{attr} as head_{attr},'

    queries = {}
    # body event (condition) left join head event
    base_table_query = f'''
    with base as ( 
    select 
        body.event_report_time as body_event_report_time,
        body.event_type_name as body_event_type_name,
        body.event_time as body_event_time,
        body.event_id as body_event_id,
        {attributes_select}
        head.event_report_time as head_event_report_time,
        head.event_type_name as head_event_type_name,
        head.event_time as head_event_time,
        head.event_id as head_event_id
    from {EVENT_TABLE} as body
    left join {EVENT_TABLE} as head
        on {condition}head.event_type_name='{c.head_event_type_name}'
    where body.event_type_name='{c.body_event_type_name}'
    )
    '''

    if c.min_delay:
        min_delay_violation_query = base_table_query + f'''
        select * from base where body_event_time + {c.min_delay} < head_event_time;
        '''
        # there is a corresponding violation handling, which should be deleting both (parsing should handle this)
        if ("TIME UNDER", (c.body_event_label, c.head_event_label)) in c.violation_handling:
            queries["TIME UNDER"] = min_delay_violation_query

    if c.max_count:
        max_count_violation_query = base_table_query + '''
        select *, count(head_event_id) as count from base
        group by body_event_id
        having count > 1;
        '''
        # there is a corresponding violation handling, which should be deleting the head event in the current batch (parsing should handle this)
        if ("COUNT OVER", (c.head_event_label)) in c.violation_handling:
            queries["COUNT OVER"] = max_count_violation_query

    return queries


if __name__ == '__main__':
    # create_event_table()
    # create_body_assignment(r=r)
    # create_head_assignment(r=r)
    queries = constraint_translation(c=c1)
    # print(queries)

    # sanity checking
    for violation, query in queries.items():
        print(query)
        try:
            cursor.execute(query)
        except sqlite3.Error as e:
            print(f"Error: {e}")
