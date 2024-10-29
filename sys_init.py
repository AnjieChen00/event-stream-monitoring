from definitions import *
from helper import *
import time
import sqlite3


# based on the event type objects, create the event table using sql in sqlite
def create_event_table(EventTypeList=event_stream, con=con, cur=cur):
    # constructing the attributes' sql
    attributes_sql = ''

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
        cur.execute(create_sql)
    except sqlite3.Error as e:
        print(f"Error: {e}")
    return


def create_body_assignment(r: Rule, con=con, cur=cur):
    '''
    r need to be a rule class
    '''
    attributes_sql = ''
    time_var_sql = ''

    all_time_vars = r.body_time_vars

    attribute_type_mapping = {}

    for atom in r.body:
        if isinstance(atom, EventAtom):
            atom_event_type = fetch_type_definition_from_stream_definition(event_type_name=atom.predicate)
            # we should be only selecting the attributes that is in the rule
            for attr, type in atom_event_type.attributes.items():
                if attr in r.body_attributes:
                    attribute_type_mapping[attr] = type

    for attr, type in attribute_type_mapping.items():
        attributes_sql += f'{attr} {type},'

    for time_var in list(all_time_vars):
        time_var_sql += f'{time_var} INTEGER, {time_var}' + '_prime INTEGER,'

    create_ba_sql = f'''
    CREATE TABLE IF NOT EXISTS body_assignment_{r.rule_id} (
    aid TEXT,
    Associated_event_ids TEXT,
    {attributes_sql}
    {time_var_sql}
    matched BOOLEAN DEFAULT False, 
    PRIMARY KEY (aid)
    )
    '''
    # BLOB is storing serialized python objects by pick.dumps(obj)
    print(f"BA creation sql: {create_ba_sql}")

    try:
        cur.execute(create_ba_sql)
    except sqlite3.Error as e:
        print(f"Error: {e}")

    return

def create_head_assignment(r: Rule, con=con, cur=cur):
    '''
    r need to be a rule class
    '''
    attributes_sql = ''
    time_var_sql = ''

    all_time_vars = r.head_time_vars

    attribute_type_mapping = {}

    for atom in r.head:
        if isinstance(atom, EventAtom):
            atom_event_type = fetch_type_definition_from_stream_definition(event_type_name=atom.predicate)
            # we should be only selecting the attributes that is in the rule
            for attr, type in atom_event_type.attributes.items():
                if attr in r.head_attributes:
                    attribute_type_mapping[attr] = type

    for attr, type in attribute_type_mapping.items():
        attributes_sql += f'{attr} {type},'

    for time_var in list(all_time_vars):
        time_var_sql += f'{time_var} INTEGER, {time_var}' + '_prime INTEGER,'

    create_ha_sql = f'''
    CREATE TABLE IF NOT EXISTS head_assignment_{r.rule_id} (
    aid TEXT,
    Associated_event_ids TEXT,
    {attributes_sql}
    {time_var_sql}
    PRIMARY KEY (aid)
    )
    '''
    # BLOB is storing serialized python objects by pick.dumps(obj)
    print(f'HA creation sql: {create_ha_sql}')

    try:
        cur.execute(create_ha_sql)
    except sqlite3.Error as e:
        print(f"Error: {e}")

    return

def create_extension_table(r: Rule, con=con, cur=cur):

    sql = f'''
    CREATE TABLE IF NOT EXISTS extension_{r.rule_id} (
    bid TEXT,
    hid TEXT,
    deadline INTEGER
    );
    '''
    try:
        cur.execute(sql)
        print(f'EXT creation sql: {sql}')
    except sqlite3.Error as e:
        print(f"Error: {e}")


def create_assignment_database(rules, con=con, cur=cur):
    for r in rules:
        create_body_assignment(r, con=con, cur=cur)
        create_head_assignment(r, con=con, cur=cur)
        create_extension_table(r, con=con, cur=cur)
    return True


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
        # max(head_event_report_time) as latest_head_event_report_time,
        max_count_violation_query = base_table_query + '''
        SELECT b1.body_event_id as body_event_id,
        b1.head_event_id as head_event_id
        FROM base AS b1
        JOIN (
            SELECT body_event_id, MAX(head_event_report_time) AS latest_head_event_report_time
            FROM base
            GROUP BY body_event_id
            HAVING COUNT(head_event_id) > 1
        ) AS b2
        ON b1.body_event_id = b2.body_event_id
        AND b1.head_event_report_time = b2.latest_head_event_report_time;
        '''
        # there is a corresponding violation handling, which should be deleting the head event in the current batch (parsing should handle this)
        if ("COUNT OVER", (c.head_event_label)) in c.violation_handling:
            queries["COUNT OVER"] = max_count_violation_query

    return queries

