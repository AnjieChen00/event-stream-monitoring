from definitions import *
from helper import *
import time
from sys_init import *
import sqlite3

# read and store window size's events to database

# the new-coming events are dumped as a file in the events/ folder
# ideally this process should be triggered whenever the new.txt got refreshed

##### After batch processing, we would have the database in place (the new event batch, all business rule's BA, HA and EXT tables), ready for the algorithm


def parse_batches_generator(file_path: str, event_folder=EVENT_FOLDER):
    with open(event_folder + file_path, 'r') as f:
        current_batch = None
        timestamp = None

        for line in f:
            line = line.strip()

            print(f'parsing line {line}')

            if ':' in line and not line[1:-1].startswith('event_type_name'):
                # If we encounter a new batch while processing an existing batch, yield the existing one
                if current_batch:
                    yield current_batch

                batch_id, timestamp = line.split(':')

                current_batch = {
                    'batch_id': batch_id.strip(),
                    'timestamp': int(timestamp.strip()),
                    'events': []
                }
            elif line == 'END':
                # End of the current batch, yield the batch
                if current_batch:
                    yield current_batch
                    current_batch = None
            else:
                # Parse the event line and store it as a dictionary
                if current_batch:
                    event_dict = parse_event(line[1:-1], current_batch['timestamp'])
                    current_batch['events'].append(event_dict)


def parse_event(event_str, timestamp):
    """
    Parse an event string and return it as a dictionary.
    Add the timestamp field.
    """
    event_dict = {}

    # Start with the timestamp
    event_dict['event_report_time'] = timestamp

    # Split the event string into key-value pairs
    parts = event_str.split(';')
    for part in parts:
        # returns the lowest index or first occurrence of the substring
        index = part.find(':')
        key, value = part[:index], part[index+1:]
        event_dict[key.strip()] = value.strip()

    return event_dict


def delete_old_events(batch_timestamp: int, window_size=WINDOW_SIZE, con=con, cur=cur):
    sql = f'''
    DELETE FROM events
    WHERE event_time < {batch_timestamp} - {window_size};
    '''
    res = cur.execute(sql)
    con.commit()
    return res


def event_insert_row_from_dict(row_dict, table_name=EVENT_TABLE, cur=cur, con=con):
    # Build the SQL query dynamically
    columns = ''
    values = ''

    for column_name, value in row_dict.items():
        columns += (column_name + ',')
        if column_name=='event_time' or column_name=='event_report_time':
            values += (str(value) + ',')
        else:
            values += (f"'{value}'" + ",")
    columns = columns[:-1]
    values = values[:-1]

    execute_insertion(table_name, columns, values)


def store_events(event_batch: dict, batch_timestamp: int, event_folder=EVENT_FOLDER, window_size=WINDOW_SIZE, cur=cur):
    # print(f"Batch ID: {batch['batch_id']}, Timestamp: {batch['timestamp']}")
    for row_dict in event_batch:
        print(row_dict)  # Print the event dictionary

        type_def = fetch_type_definition_from_stream_definition(event_type_name=row_dict['event_type_name'])
        print(f"DEBUG - fetching type definition for event type name: {row_dict['event_type_name']}")
        unique_keys = list(type_def.unique)
        ############ check max delay constraint ###########
        max_delay = type_def.max_delay_scope
        if int(row_dict['event_report_time']) - int(row_dict['event_time']) > max_delay:
            print(f'{row_dict} not inserted because report time was delayed too much')
            continue
        ############ check window_size --- implication: max_delay < window_size####################
        if int(row_dict['event_time']) < batch_timestamp - window_size:
            continue
        ########### generate an event id and add to row dict ############
        # need to specify the order or use hash function?
        row_dict['event_id'] = row_dict['event_type_name'] + '_'.join(row_dict[key] for key in unique_keys)
        ############# insert the row ###############################
        event_insert_row_from_dict(row_dict=row_dict, cur=cur)


def form_deletion_set(cur=cur):
    deletion_set = set()
    for c in constraints:
        queries = constraint_translation(c)
        for handling, query in queries.items():
            rows = cur.execute(query).fetchall()
            if handling == 'COUNT OVER':
                for row in rows:
                    deletion_set.add(row['head_event_id'])
            if handling == 'TIME UNDER':
                for row in rows:
                    deletion_set.add(row['body_event_id'])
                    deletion_set.add(row['head_event_id'])
    return list(deletion_set)

def deletion_from_events(deletion_list, con=con, cur=cur):
    for event_id in deletion_list:
        sql = f'''delete from {EVENT_TABLE}
        where event_id={event_id};
        '''
        res = cur.execute(sql)
        con.commit()
        print(f'successful deleted event_id {event_id}')


def deletion_from_BA(deletion_list, rules=rules, con=con, cur=cur):
    Bids = {}
    for event_id in deletion_list:
        for r in rules:
            rule_id = r.rule_id
            sql_select = f'''
                            SELECT Bid 
                            FROM body_assignment_{rule_id}
                            WHERE Associated_event_ids LIKE '%{event_id}%'
                        '''
            try:
                cur.execute(sql_select)
                rows = cur.fetchall()
                # Collect the Bids of the rows to be deleted
                Bids[rule_id] = [row['Bid'] for row in rows]

                delete_sql = f'''delete from body_assignment_{rule_id}
                where Associated_event_ids like '%{event_id}%'
                '''
                cur.execute(delete_sql)
                con.commit()
            except:
                print('Deletion from BA failed')

    return Bids


def deletion_from_HA(deletion_list, rules=rules, con=con, cur=cur):
    Hids = {}
    for event_id in deletion_list:
        for r in rules:
            rule_id = r.rule_id
            sql_select = f'''
                            SELECT Hid 
                            FROM body_assignment_{rule_id}
                            WHERE Associated_event_ids LIKE '%{event_id}%'
                        '''
            try:
                cur.execute(sql_select)
                rows = cur.fetchall()
                # Collect the Hids of the rows to be deleted
                Hids[rule_id] = [row['Hid'] for row in rows]
                delete_sql = f'''delete from head_assignment_{rule_id}
                where Associated_event_ids like '%{event_id}%'
                '''
                cur.execute(delete_sql)
                con.commit()

            except:
                print('Deletion from BA failed')
    return Hids


def delete_from_EXT(Bids: dict, Hids: dict, con=con, cur=cur):
    for rule_id, bids in Bids.items():
        # if a bid got deleted, then we should delete the bid row in EXT
        for bid in bids:
            delete_sql = f'''delete from extension_{rule_id}
                       where Bid='{bid}'
                       '''
            try:
                cur.execute(delete_sql)
                con.commit()
            except:
                print(f'Deletion of bid {bid} failed')

    for rule_id, hids in Hids.items():
        # if a hid got deleted, then we should delete the row that uses hid as head,
        # and the deadline was also recalculated with 'bid, -, ddl'
        for hid in hids:
            delete_sql = f'''delete from extension_{rule_id}
                        where Hid='{hid}'
                        '''
            try:
                cur.execute(delete_sql)
                con.commit()
            except:
                print(f'Deletion of hid {hid} failed')


# def event_handler(event_folder=EVENT_FOLDER, window_size=WINDOW_SIZE, con=con, cur=cur):
#     delete_old_events(window_size, cur=cur)
#     store_events(event_folder, window_size)
#     deletion_list = form_deletion_set(cur=cur)
#     # carry out deletion in the event table
#     deletion_from_events(deletion_list=deletion_list, cur=cur)
#     # carry out deletion in all the BA, HA, and EXT
#     Bids = deletion_from_BA(deletion_list=deletion_list, cur=cur)
#     Hids = deletion_from_HA(deletion_list=deletion_list, cur=cur)
#     delete_from_EXT(Bids=Bids, Hids=Hids)
#
#     con.close()
#
#
# if __name__ == '__main__':
#     # unit testing
#     event_handler()

