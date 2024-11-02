from copy import deepcopy

from matplotlib.table import table
from pandas.core.ops import arithmetic_op
from sympy.multipledispatch.conflict import consistent

from definitions import *
from sys_init import *
from helper import *
from batch_processing import *
from tabulate import tabulate

def remove_attribute_vars_from_gap_atoms(r: Rule) -> Rule:
    eliminate_from_body = set()
    for atom in r.body_arithmetic_atoms:
        for var in atom.variables:
            if var in r.body_attributes:
                eliminate_from_body.add(var)
    eliminate_from_body = list(eliminate_from_body)

    body_tmp = r.body_arithmetic_atoms
    for v in eliminate_from_body:
        body_tmp = eliminate_var(var=v, atoms=body_tmp)
    # simply inequalities
    body_tmp = simplify_inequalities(inequalities=body_tmp)


    eliminate_from_head = set()
    for atom in r.head_arithmetic_atoms:
        for var in atom.variables:
            if var in r.body_attributes or var in r.head_attributes:
                eliminate_from_head.add(var)
    eliminate_from_head = list(eliminate_from_head)

    head_tmp = r.body_arithmetic_atoms + r.head_arithmetic_atoms

    for v in eliminate_from_head:
        # print(f'eliminating {v}')
        head_tmp = eliminate_var(var=v, atoms=head_tmp)
        # for each in head_tmp:
            # print(each)
        # print('-'* 50)
    # simply inequalities
    head_tmp = simplify_inequalities(inequalities=head_tmp)

    new_r = Rule(rule_id=r.rule_id, body=r.body_event_atoms+body_tmp, head=r.head_event_atoms+head_tmp)

    return new_r


def deadline(gap_atoms: list[ArithmeticAtom], time_var_assignment: dict) -> int:
    # step 1: find all the time variables present in those gap atoms
    upperbd = {}
    for atom in gap_atoms:
        for var in atom.variables:
            if var not in upperbd:
                upperbd[var] = float('inf')

    time_vars = [x for x in upperbd.keys()]
    # print(f'time vars: {time_vars}')

    # step 2: if the assignment is already unsatisfiable on those gap atoms, return the max assignment value
    if not sat_test(gap_atoms, time_var_assignment):
        return max(time_var_assignment.values())

    # step3: u + k <= v, k, v should be constants
    for i in range(len(gap_atoms)):
        gap_atoms[i] = inequality_formatter(gap_atoms[i])

    for atom in gap_atoms:
        if len(atom.variables) == 2:
            var1, var2 = atom.variables[0], atom.variables[1]
            coef1, coef2 = atom.coefficient_vector[0], atom.coefficient_vector[1]
            if coef1 == 1 and coef2 == -1:
                # var2 on the right
                if var1 not in time_var_assignment and var2 in time_var_assignment:
                    upperbd[var1] = time_var_assignment[var2] + atom.right_constant
            elif coef1 == -1 and coef2 == 1:
                # var1 on the right
                if var2 not in time_var_assignment and var1 in time_var_assignment:
                    upperbd[var2] = time_var_assignment[var1] + atom.right_constant
            else:
                print(f'{atom} is not a gap atom')
        elif len(atom.variables) == 1:
            if atom.variables[0] not in time_var_assignment:
                upperbd[atom.variables[0]] = atom.right_constant

    # step 4: m + k <= u (m, u are time vars, k is constant) ==> upperbd[m] = (upperbd(u) - k, upperbd[m])
    for i in range(len(gap_atoms)):
        for atom in gap_atoms:
            if len(atom.variables) == 2:
                var1, var2 = atom.variables[0], atom.variables[1]
                coef1, coef2 = atom.coefficient_vector[0], atom.coefficient_vector[1]
                if coef1 == 1 and coef2 == -1:
                    # var2 on the right
                    upperbd[var1] = min(upperbd[var1], upperbd[var2] + atom.right_constant)
                elif coef1 == -1 and coef2 == 1:
                    # var1 on the right
                    upperbd[var2] = min(upperbd[var2], upperbd[var1] + atom.right_constant)

    return int(min([x for x in upperbd.values()]))


def extended_deadline(rule: Rule, time_var_assignment: dict) -> int:
    # step 1: find all max delay of each event type of all the event atoms
    max_delay_gap_atoms = []
    time_var_to_eliminate = []

    all_event_atoms = rule.body_event_atoms + rule.head_event_atoms
    all_gap_atoms = rule.body_arithmetic_atoms + rule.head_arithmetic_atoms

    for event_atom in all_event_atoms:
        time_var = event_atom.timestamp_variable
        event_type_def = fetch_type_definition_from_stream_definition(event_type_name=event_atom.predicate)
        if event_type_def:
            max_delay = event_type_def.max_delay_scope
            report_time_var = time_var + '_r'
            # two arithmetic atoms added to list
            max_delay_gap_atoms.append(ArithmeticAtom(variables=[time_var, report_time_var], coefficient_vector=[1, -1],
                                                      comparative_operator= '<=', right_constant=0))
            max_delay_gap_atoms.append(ArithmeticAtom(variables=[report_time_var, time_var], coefficient_vector=[1, -1],
                                                      comparative_operator= '<=', right_constant=max_delay))
            time_var_to_eliminate.append(time_var)
        else:
            print('event type definition not found')

    all_gap_atoms = all_gap_atoms + max_delay_gap_atoms

    tmp = deepcopy(all_gap_atoms)
    for var in time_var_to_eliminate:
        tmp = eliminate_var(var=var, atoms=tmp)

    # all gap atoms' time vars are in event report time space now

    report_time_var_assignment = {}
    for time_var, value in time_var_assignment.items():
        report_time_var_assignment[time_var + '_r'] = value

    extended_ddl = deadline(gap_atoms=tmp, time_var_assignment=report_time_var_assignment)
    return extended_ddl

def get_event_batch(batch_timestamp: int,event_table=EVENT_TABLE, conn=con, cur=cur) -> list[dict]:
    get_sql = f'''select * from {event_table} where event_report_time={batch_timestamp};'''
    try:
        cur.execute(get_sql)
        rows = cur.fetchall()
        columns = [description[0] for description in cur.description]
        # Convert rows to a list of dictionaries
        result = [dict(zip(columns, row)) for row in rows]
        return result
    except Exception as e:
        print(f"Error occurred while getting the event batch: {e}")
        return []

def get_next_aid(table_name: str, cur=cur, con=con) -> str:
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cur.fetchone()[0]
    row_count = int(row_count)
    return f'{table_name}_{row_count + 1}'

def insert_row_to_table(row_dict: dict, table_name: str, cur=cur, con=con) -> int:
    columns = ', '.join(row_dict.keys())
    placeholders = ', '.join(['?' for _ in row_dict.keys()])
    values = tuple(row_dict.values())

    insert_sql = f'''
    INSERT INTO {table_name} ({columns}) VALUES ({placeholders})
    '''
    try:
        # Execute the query with dynamic column names and values
        cur.execute(insert_sql, values)
        con.commit()
        # print("Row inserted successfully.")
        return True
    except Exception as e:
        print(f"Error occurred: {e}")
        return False

def merge(assignment_table_name: str, time_vars: list[str], attributes: list[str], new_assignments: list[dict], con=con, cur=cur) -> list[dict]:
    different_condition = ''

    for _ in new_assignments:
        different_condition += f'''aid != '{_["aid"]}' AND '''

    merged_rows_dicts = []

    for new_assignment in new_assignments:
        attributes_condition = ''
        for attr in attributes:
            if attr in new_assignment and new_assignment[attr] is not None:
                attributes_condition += f"({attr}='{new_assignment[attr]}' OR {attr} is Null) AND "

        time_vars_condition = ''
        for time_var in time_vars:
            if time_var in new_assignment and new_assignment[time_var] is not None:
                time_vars_condition += f'({time_var}={new_assignment[time_var]} OR {time_var} is Null) AND '

        find_consistent_rows_query = f'''select * 
        from {assignment_table_name}
        where {different_condition} 
        {attributes_condition}
        {time_vars_condition[:-4]} 
        '''
        if assignment_table_name.startswith('body'):
            find_consistent_rows_query += ' AND matched=0;'
        elif assignment_table_name.startswith('head'):
            find_consistent_rows_query += ';'

        print(f"debug - merge: {find_consistent_rows_query}")
        # print_table(table_name=assignment_table_name)

        try:
            cur.execute(find_consistent_rows_query)
            consistent_rows = cur.fetchall()
            column_names = [description[0] for description in cur.description]
            # Convert rows to list of dictionaries
            consistent_rows_dicts = [dict(zip(column_names, row)) for row in consistent_rows]
        except Exception as e:
            print(f"Error occurred in merge {find_consistent_rows_query} : {e}")
            consistent_rows_dicts = []

        for consistent_rows_dict in consistent_rows_dicts:
            # print(consistent_rows_dict) # this will have all the columns as keys from the Assignment table
            # print(new_assignment)
            # print('*'* 100)
            tmp = copy.deepcopy(consistent_rows_dict)
            tmp['aid'] = None
            for col_name, value in consistent_rows_dict.items():
                if col_name == 'Associated_event_ids':
                    tmp[col_name] += f'+{new_assignment[col_name]}'
                elif col_name in new_assignment and col_name != 'aid':
                    if value is None and new_assignment[col_name] is not None:
                        tmp[col_name] = new_assignment[col_name]
                    elif value is not None and new_assignment[col_name] is None:
                        tmp[col_name] = value
                    elif value is None and new_assignment[col_name] is None:
                        tmp[col_name] = None
                    else:
                        if new_assignment[col_name] == value:
                            tmp[col_name] = value
                        else:
                            print(f'{col_name} are inconsistent')
            merged_rows_dicts.append(tmp)

    return merged_rows_dicts



def update_assignment_table(event_atoms: list[EventAtom], gap_atoms: list[ArithmeticAtom], time_vars: list[str], attributes: list[str], event_batch: list[dict], batch_timestamp: int, table_name: str):
    newly_inserted_assignments = []
    for event in event_batch:
        print(f'update_assignment_table DEBUG - processing event {event} \n for table {table_name} \n')
        for event_atom in event_atoms:
            time_var = event_atom.timestamp_variable
            event_type = fetch_type_definition_from_stream_definition(event_type_name=event_atom.predicate)
            if event_type.event_type_name == event['event_type_name']:

                # # I actually don't need to evaluate and store evaluated gap atoms, because I know what gap atoms are there and what are the assignments already
                # gap_atoms_evaluated = evaluate(gap_atoms=gap_atoms, time_var_assignments={time_var: event['event_time']})

                # create assignment
                assignment = {'aid': get_next_aid(table_name=table_name),
                              'Associated_event_ids': event['event_id'],
                              f'{time_var}' + '_prime': batch_timestamp
                              # 'gap_atoms': pickle.dumps(gap_atoms_evaluated)
                              }

                for event_attr, value in event.items():
                    if event_attr == 'event_time' or event_attr in attributes:
                        if event_attr != 'event_time':
                            assignment[event_attr] = value
                        else:
                            assignment[time_var] = value

                # print(f'the assignment is {assignment}')
                print(f'update_assignment_table DEBUG - inserting the assignment {assignment} to the {table_name} table')
                res = insert_row_to_table(row_dict=assignment, table_name=table_name)
                if res:
                    newly_inserted_assignments.append(assignment)

    if newly_inserted_assignments:
        # for each pair of unique and consistent rows (func to find them), merge and get a new assignment

        # Method: formulate the new rows as the query result
        merged_rows = merge(assignment_table_name=table_name, time_vars=time_vars, attributes=attributes, new_assignments=newly_inserted_assignments)
        print(f"DEBUG - merged_rows of table {table_name}: {merged_rows}")

        # insert the merged_rows (aid generated)
        for row in merged_rows:
            # re-evaluate the assignment: sat test
            time_var_assignments = {}
            for key, value in row.items():
                if key in time_vars:
                    time_var_assignments[key] = value
            if sat_test(arithmetic_atoms=gap_atoms, assignment_dict=time_var_assignments):
                row['aid'] = get_next_aid(table_name=table_name)
                # row['gap_atoms'] = evaluate(gap_atoms=gap_atoms, time_var_assignments=time_var_assignments)
                res = insert_row_to_table(row_dict=row, table_name=table_name)

    # print(f'assignment table {table_name} update completed on this event batch')


def find_newly_complete_body_assignment(body_table: str, time_vars: list, batch_timestamp: int) -> list[str]:
    '''
    return result as [bid1, bid2....] ; attribute and time var values can be queried using sql
    '''
    time_vars_condition_not_null = ''
    time_vars_condition_new = '('
    for time_var in time_vars:
        time_vars_condition_not_null += f'{time_var} is not NULL and '
    for time_var in time_vars:
        time_vars_condition_new += f'{time_var}' + '_prime' + f'={batch_timestamp} or '
    time_vars_condition_new = time_vars_condition_new[:-3] + ')'

    time_vars_condition = time_vars_condition_not_null + time_vars_condition_new

    find_sql = f'''select aid from {body_table}
    where {time_vars_condition};
    '''

    print(f'query used to find newly updated and complete body aid: \n{find_sql}')

    try:
        cur.execute(find_sql)
        aids = cur.fetchall()
        aids = [x[0] for x in aids]

        return aids

    except Exception as e:
        print(f"Error occurred: {e}")
        return []

def find_newly_updated_head_assignment(head_table: str, time_vars: list, batch_timestamp: int) -> list[str]:
    '''
    head assignment does not have to be complete;
    '''
    time_vars_condition_batch_ts = ''
    for time_var in time_vars:
        time_vars_condition_batch_ts += f'{time_var}' + '_prime' + f'={batch_timestamp} or'
    time_vars_condition_batch_ts = time_vars_condition_batch_ts[:-3]

    find_sql = f'''select aid from {head_table}
    where {time_vars_condition_batch_ts};
    '''
    print(f'query used to find newly updated head aid: \n{find_sql}')

    try:
        cur.execute(find_sql)
        aids = cur.fetchall()
        aids = [x[0] for x in aids]

        return aids

    except Exception as e:
        print(f"Error occurred: {e}")
        return []


def extends(body_table: str, head_table: str, existing_bid: str, existing_hid: str, new_hid: str, r: Rule) -> int:
    '''
    if new hid extends the existing bid AND hid
    '''

    select_existing_bid = f'''select {', '.join(r.body_attributes)}, {', '.join(r.body_time_vars)}
    from {body_table} where aid='{existing_bid}';
    '''
    try:
        cur.execute(select_existing_bid)
        body_rows = cur.fetchall()
        column_names = [description[0] for description in cur.description]
        # Convert rows to list of dictionaries
        body_rows_dict = [dict(zip(column_names, row)) for row in body_rows]
        # print(f'body_rows_dict: {body_rows_dict}')
    except Exception as e:
        body_rows_dict = {}
        print(f"Error occurred when executing {select_existing_bid}: {e}")

    select_existing_hid = f'''select {', '.join(r.head_attributes)}, {', '.join(r.head_time_vars)}
    from {head_table} where aid='{existing_hid}';
    '''
    try:
        cur.execute(select_existing_hid)
        head_rows = cur.fetchall()
        column_names = [description[0] for description in cur.description]
        # Convert rows to list of dictionaries
        head_rows_dict = [dict(zip(column_names, row)) for row in head_rows]
        # print(f'head_rows_dict: {head_rows_dict}')
    except Exception as e:
        head_rows_dict = {}
        print(f"Error occurred when executing {select_existing_hid}: {e}")

    select_new_hid = f'''select {', '.join(r.head_attributes)}, {', '.join(r.head_time_vars)}
    from {head_table} where aid='{new_hid}';
    '''
    try:
        cur.execute(select_new_hid)
        new_head_rows = cur.fetchall()
        column_names = [description[0] for description in cur.description]
        if len(new_head_rows) != 1:
            print(f'debug - extends - selecting new hid {new_hid} failed')
            new_head_rows_dict = {}
        else:
            # Convert rows to list of dictionaries
            new_head_rows_dict = dict(zip(column_names, new_head_rows[0]))
            # print(f'head_rows_dict: {new_head_rows_dict}')
    except Exception as e:
        new_head_rows_dict = {}
        print(f"Error occurred when executing {select_new_hid}: {e}")

    for key, value in new_head_rows_dict.items():
        if key in body_rows_dict:
            if value != body_rows_dict[key]:
                return False
        if key in head_rows_dict:
            if value != head_rows_dict[key]:
                return False
    return True


def check_if_assignment_complete(hid: str, head_time_vars: list, head_table_name: str, con=con, cur=cur) -> int or None:
    # Construct SQL conditions for each time variable
    not_null_conditions = ' AND '.join([f"{var} IS NOT NULL AND typeof({var}) = 'integer'" for var in head_time_vars])

    check_sql = f'''select 1 from {head_table_name} 
    where aid='{hid}' AND {not_null_conditions};'''

    print(f'check_sql - check_if_assignment_complete: {check_sql}')
    try:
        cur.execute(check_sql)
        res = cur.fetchall()

        # Return True if the query found a matching row, otherwise False
        return res is not None
    except Exception as e:
        print(f"Error occurred - check_if_assignment_complete: {e}")
        return None


def mark_bid_complete(body_table_name: str, bid: str) -> int:
    # Prepare the SQL statement to update the 'match' column
    update_sql = f"UPDATE {body_table_name} SET matched = ? WHERE aid = ?;"
    try:
        cur.execute(update_sql, (True, bid))
        con.commit()
        return True

    except Exception as e:
        print(f"Error occurred - mark_bid_complete: {e}")
        return False


def update_extension_table(body_table_name: str, head_table_name: str, extension_table_name: str, r: Rule, batch_timestamp: int):
    # for each complete body assignment (all time_var are assigned in the body_table_name)
    newly_complete_bids = find_newly_complete_body_assignment(body_table=body_table_name, time_vars=r.body_time_vars, batch_timestamp=batch_timestamp)
    for bid in newly_complete_bids:
        find_time_var_assignment = f'''select {', '.join(r.body_time_vars)}
            from {body_table_name} where aid='{bid}';
            '''
        try:
            cur.execute(find_time_var_assignment)
            body_rows = cur.fetchall()
            column_names = [description[0] for description in cur.description]
            if len(body_rows) != 1:
                print(f'debug - update_extension_table - {body_table_name} find time var assignment of aid {bid} failed')
                body_time_var_assignment = {}
            else:
                # Convert rows to list of dictionaries
                body_time_var_assignment = dict(zip(column_names, body_rows[0]))
                # print(f'body_rows_dict: {body_time_var_assignment}')
        except Exception as e:
            body_time_var_assignment = {}
            print(f"Error occurred when executing {find_time_var_assignment}: {e}")
        # add row to EXT
        ext_row = {'bid': bid, 'hid': None, 'deadline': extended_deadline(rule=r, time_var_assignment=body_time_var_assignment)}
        res = insert_row_to_table(row_dict=ext_row, table_name=extension_table_name)
        # print(f'EXT insertion: {res}')

    # for each newly updated hid
    hids = find_newly_updated_head_assignment(head_table=head_table_name, time_vars=r.head_time_vars, batch_timestamp=batch_timestamp)
    for hid in hids:
        # for each row in the EXT table
        ext_query = f'''select * from {extension_table_name};'''
        try:
            cur.execute(ext_query)
            rows = cur.fetchall()
        except Exception as e:
            rows = []

        for (ebid, ehid, ddl) in rows:

            if extends(body_table=body_table_name, head_table=head_table_name, existing_bid=ebid, existing_hid=ehid, new_hid=hid, r=r):
                body_select_sql = f"select {', '.join(r.body_time_vars)} from {body_table_name} where aid='{ebid}';"
                try:
                    cur.execute(body_select_sql)
                    body_rows = cur.fetchall()
                    column_names = [description[0] for description in cur.description]
                    if len(body_rows) != 1:
                        print(f'debug - update_extension_table - {body_table_name} find time var assignment of aid {ebid} failed')
                        body_time_var_assignment = {}
                    else:
                        # Convert rows to list of dictionaries
                        body_time_var_assignment = dict(zip(column_names, body_rows[0]))
                        # print(f'body_rows_dict: {body_time_var_assignment}')
                except Exception as e:
                    body_time_var_assignment = {}
                    print(f"Error occurred when executing {body_select_sql}: {e}")

                if ehid:
                    head_select_sql = f"select {', '.join(r.head_time_vars)} from {head_table_name} where aid='{ehid}';"
                    try:
                        cur.execute(head_select_sql)
                        head_rows = cur.fetchall()
                        column_names = [description[0] for description in cur.description]
                        if len(head_rows) != 1:
                            print(f'debug - update_extension_table - {head_table_name} find time var assignment of aid {ehid} failed')
                            head_time_var_assignment = {}
                        else:
                            # Convert rows to list of dictionaries
                            head_time_var_assignment = dict(zip(column_names, head_rows[0]))
                            # print(f'head_rows_dict: {head_time_var_assignment}')
                    except Exception as e:
                        head_time_var_assignment = {}
                        print(f"Error occurred when executing {head_select_sql}: {e}")
                else:
                    head_time_var_assignment = {}

                assignment_dict = {**body_time_var_assignment, **head_time_var_assignment}

                if sat_test(arithmetic_atoms=r.body_arithmetic_atoms+r.head_arithmetic_atoms, assignment_dict=assignment_dict):
                    # add row to EXT
                    if check_if_assignment_complete(hid=hid, head_time_vars=r.head_time_vars, head_table_name=head_table_name, con=con, cur=cur):
                        ext_row = {'bid': ebid, 'hid': hid, 'Deadline': None}
                        # mark bid row in the BA table as complete
                        mark_bid_complete(body_table_name=body_table_name, bid=ebid)
                    else:
                        ext_row = {'bid': ebid, 'hid': hid,
                                   'Deadline': extended_deadline(rule=r, time_var_assignment=assignment_dict)}
                    res = insert_row_to_table(row_dict=ext_row, table_name=extension_table_name)
                    # print(f'EXT insertion: {res}')


def detect(extension_table_name: str, batch_timestamp: int) -> dict[str: list[tuple]]:
    detect_sql = f'''select bid, hid from {extension_table_name}
    where deadline < {batch_timestamp}
    '''
    try:
        cur.execute(detect_sql)
        rows = cur.fetchall()
        violation = {extension_table_name: [row for row in rows]}
        return violation
    except Exception as e:
        print(f"Error occurred: {e}")
        return {extension_table_name: []}


def print_table(table_name: str, cur=cur, con=con):
    # Fetch column headers
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cur.fetchall()]  # Column names are in the second position

    # Fetch all rows from the table
    cur.execute(f"SELECT * FROM {table_name}")
    rows = cur.fetchall()

    # Print the table with headers using tabulate
    print(tabulate(rows, headers=columns, tablefmt="grid"))


def orchestrator(event_folder=EVENT_FOLDER, file_path=EVENT_FILE, window_size=WINDOW_SIZE, con=con, cur=cur):

    batch_generator = parse_batches_generator(file_path)
    print(f"batch_generator created from parsing {file_path}")

    # Process each batch one at a time
    now = 200

    for batch in batch_generator:
        print('=' * 100)
        print(f"Now processing Batch ID: {batch['batch_id']}, Timestamp: {batch['timestamp']}")

        batch_id = batch['batch_id']
        batch_timestamp = batch['timestamp']
        batch_events = batch['events']

        print(f'processing the timestamps before {batch_timestamp}')
        while now <= batch_timestamp:

            delete_old_events(batch_timestamp=now, window_size=window_size, con=con, cur=cur)
            print(f"deleted old events {WINDOW_SIZE} later than the batch timestamp {now}")

            if now == batch_timestamp:
                store_events(event_batch=batch_events, batch_timestamp=now, event_folder=event_folder, window_size=window_size, cur=cur)
                print(f"Stored the batch of {batch['batch_id']}: {batch['timestamp']} to events table")



            deletion_list = form_deletion_set(constraints=constraints, cur=cur)
            print(f"Deletion list formed: {deletion_list}")

            # carry out deletion in the event table
            deletion_from_events(deletion_list=deletion_list, con=con, cur=cur)
            print(f"deletion from the events table completed.")

            # carry out deletion in all the BA, HA, and EXT
            Bids = deletion_from_BA(deletion_list=deletion_list, rules=rules, cur=cur)
            print(f"deletion from the all BA table completed : {Bids}")

            Hids = deletion_from_HA(deletion_list=deletion_list, rules=rules, cur=cur)
            print(f"deletion from the all HA table completed : {Hids}")

            delete_from_EXT(Bids=Bids, Hids=Hids)
            print(f"deletion from the all EXT table completed ")

            insert_internal_events_from_all_cal_rules(cal_rules=cal_rules, now=now, con=con, cur=cur)

            print_table(table_name='events')

            print("################ batch processing complete, violation detection starts ####################")
            all_violations = {}
            prepared_event_batch = get_event_batch(event_table=EVENT_TABLE, batch_timestamp=now, conn=con, cur=cur)
            print(f'the event batch that algorithm is going to run on: {prepared_event_batch} \n')

            for r in rules:
                update_assignment_table(event_atoms=r.body_event_atoms, gap_atoms=r.body_arithmetic_atoms,
                                        time_vars=r.body_time_vars, attributes=r.body_attributes, event_batch=prepared_event_batch,
                                        batch_timestamp=now,
                                        table_name='body_assignment_' + str(r.rule_id))
                print_table(table_name='body_assignment_' + str(r.rule_id))

                update_assignment_table(event_atoms=r.head_event_atoms, gap_atoms=r.head_arithmetic_atoms,
                                        time_vars=r.head_time_vars, attributes=r.head_attributes, event_batch=prepared_event_batch,
                                        batch_timestamp=now,
                                        table_name='head_assignment_' + str(r.rule_id))
                print_table(table_name='head_assignment_' + str(r.rule_id))

                update_extension_table(body_table_name='body_assignment_' + str(r.rule_id),
                                       head_table_name='head_assignment_' + str(r.rule_id),
                                       extension_table_name='extension_' + str(r.rule_id), r=r, batch_timestamp=now)
                print_table(table_name='extension_' + str(r.rule_id))

                violations_of_this_rule = detect(extension_table_name='extension_' + str(r.rule_id), batch_timestamp=now)
                all_violations.update(violations_of_this_rule)

            print(f"violation at timestamp{now}: {all_violations}")
            now += 1