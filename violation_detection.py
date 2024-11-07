import collections
import time
from copy import deepcopy

from Tools.scripts.dutree import store
from matplotlib.table import table
from pandas.core.ops import arithmetic_op
from sympy.multipledispatch.conflict import consistent
from sympy.printing.numpy import const

from definitions import *
from sys_init import *
from helper import *
from batch_processing import *
from tabulate import tabulate

# utilize logging for large batches
import logging
logging.basicConfig(
    filename='app1106.log',        # Log file name
    filemode='a',              # Append mode; use 'w' for overwrite
    level=logging.INFO,        # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log message format
    datefmt='%Y-%m-%d %H:%M:%S'  # Date format
)

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


def deadline(gap_atoms: list[ArithmeticAtom], solver: Solver, z3_vars: dict, time_var_assignment: dict, passed_sat_test=False) -> int:
    # step 1: find all the time variables present in those gap atoms
    upperbd = {}
    for atom in gap_atoms:
        for var in atom.variables:
            if var not in upperbd:
                upperbd[var] = float('inf')

    time_vars = [x for x in upperbd.keys()]
    # print(f'time vars: {time_vars}')

    # step 2: if the assignment is already unsatisfiable on those gap atoms, return the max assignment value
    if not passed_sat_test:
        if not sat_test(solver=solver, z3_vars=z3_vars, assignment_dict=time_var_assignment):
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


def extended_deadline(rule: Rule, time_var_assignment: dict, passed_sat_test=False) -> int:

    report_time_var_assignment = {}
    for time_var, value in time_var_assignment.items():
        report_time_var_assignment[time_var + '_r'] = value

    extended_ddl = deadline(gap_atoms=rule.all_gap_atoms_in_ert_space, solver=rule.all_gap_atoms_in_ert_space_solver, z3_vars=rule.all_gap_atoms_in_ert_space_z3_vars, time_var_assignment=report_time_var_assignment, passed_sat_test=passed_sat_test)

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

        # print(f"debug - merge: {find_consistent_rows_query}")
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



def update_assignment_table(event_atoms: list[EventAtom], gap_atoms_solver: Solver, gap_atoms_z3_vars: dict, time_vars: list[str], attributes: list[str], event_batch: list[dict], batch_timestamp: int, table_name: str):
    newly_inserted_assignments = []

    # insert_time1 = time.time()
    for event in event_batch:
        # print(f'update_assignment_table DEBUG - processing event {event} \n for table {table_name} \n')
        for event_atom in event_atoms:
            time_var = event_atom.timestamp_variable
            event_type = fetch_type_definition_from_stream_definition(event_type_name=event_atom.predicate)
            if event_type.event_type_name == event['event_type_name']:

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
                # print(f'update_assignment_table DEBUG - inserting the assignment {assignment} to the {table_name} table')
                res = insert_row_to_table(row_dict=assignment, table_name=table_name)
                if res:
                    newly_inserted_assignments.append(assignment)

    if newly_inserted_assignments:
        # for each pair of unique and consistent rows (func to find them), merge and get a new assignment

        # Method: formulate the new rows as the query result
        merged_rows = merge(assignment_table_name=table_name, time_vars=time_vars, attributes=attributes, new_assignments=newly_inserted_assignments)
        # print(f"DEBUG - merged_rows of table {table_name}: {merged_rows}")

        # insert the merged_rows (aid generated)
        for row in merged_rows:
            # re-evaluate the assignment: sat test
            time_var_assignments = {}
            for key, value in row.items():
                if key in time_vars:
                    time_var_assignments[key] = value

            if sat_test(solver=gap_atoms_solver, z3_vars=gap_atoms_z3_vars, assignment_dict=time_var_assignments):
                row['aid'] = get_next_aid(table_name=table_name)
                # row['gap_atoms'] = evaluate(gap_atoms=gap_atoms, time_var_assignments=time_var_assignments)
                res = insert_row_to_table(row_dict=row, table_name=table_name)



def find_newly_complete_body_assignment(body_table: str, time_vars: list, batch_timestamp: int) -> list[dict]:
    '''
    return result as [{aid: xxx, x: ..., y: ...}] ; attribute and time var values can be queried using sql
    '''
    time_vars_condition_not_null = ''
    time_vars_condition_new = '('
    for time_var in time_vars:
        time_vars_condition_not_null += f'{time_var} is not NULL and '
    for time_var in time_vars:
        time_vars_condition_new += f'{time_var}' + '_prime' + f'={batch_timestamp} or '
    time_vars_condition_new = time_vars_condition_new[:-3] + ')'

    time_vars_condition = time_vars_condition_not_null + time_vars_condition_new

    find_sql = f'''select aid, {','.join(time_vars)} from {body_table}
    where {time_vars_condition} and matched=0;
    '''

    # print(f'query used to find newly updated and complete body aid: \n{find_sql}')

    try:
        cur.execute(find_sql)
        complete_bid_rows = cur.fetchall()
        column_names = [description[0] for description in cur.description]
        # Convert rows to list of dictionaries
        complete_bid_rows_dicts = [dict(zip(column_names, row)) for row in complete_bid_rows]
        return complete_bid_rows_dicts

    except Exception as e:
        print(f"Error occurred: {e}")
        return []

def find_newly_updated_head_assignment(head_table: str, time_vars: list, batch_timestamp: int) -> list[dict]:
    '''
    head assignment does not have to be complete;
    '''
    time_vars_condition_batch_ts = ''
    for time_var in time_vars:
        time_vars_condition_batch_ts += f'{time_var}' + '_prime' + f'={batch_timestamp} or'
    time_vars_condition_batch_ts = time_vars_condition_batch_ts[:-3]

    find_sql = f'''select aid, {','.join(time_vars)} from {head_table}
    where {time_vars_condition_batch_ts};
    '''
    # print(f'query used to find newly updated head aid: \n{find_sql}')

    try:
        cur.execute(find_sql)
        newly_updated_hid_rows = cur.fetchall()
        column_names = [description[0] for description in cur.description]
        # Convert rows to list of dictionaries
        newly_updated_hid_rows_dicts = [dict(zip(column_names, row)) for row in newly_updated_hid_rows]

        return newly_updated_hid_rows_dicts

    except Exception as e:
        print(f"Error occurred: {e}")
        return []


def extends(body_table: str, head_table: str, existing_bid: str, existing_hid: str, new_hid: str, r: Rule) -> int:
    '''
    if new hid extends the existing bid AND hid
    '''

    # new head assignment must be consistent with body assignment
    # qtime = time.time()
    body_columns = r.body_attributes + r.body_time_vars
    head_columns = r.head_attributes + r.head_time_vars

    # Prepare the columns for SELECT clause
    body_cols = ', '.join([f"b.{col} AS b_{col}" for col in body_columns])
    existing_head_cols = ', '.join([f"eh.{col} AS eh_{col}" for col in head_columns])
    new_head_cols = ', '.join([f"nh.{col} AS nh_{col}" for col in head_columns])

    # Build the LEFT JOIN query
    query = f"""
    SELECT {body_cols}, {existing_head_cols}, {new_head_cols}
    FROM {body_table} b
    LEFT JOIN {head_table} eh ON eh.aid = ?  -- existing_hid
    LEFT JOIN {head_table} nh ON nh.aid = ?  -- new_hid
    WHERE b.aid = ?  -- existing_bid
    """
    params = (existing_hid, new_hid, existing_bid)

    try:
        cur.execute(query, params)
        row = cur.fetchone()
        if row is None:
            # Handle case where existing_bid does not exist
            return False

        # Convert row to a dictionary
        row_dict = dict(row)

        # Extract dictionaries for body, existing head, and new head
        body_row_dict = {k[2:]: v for k, v in row_dict.items() if k.startswith('b_')}
        head_row_dict = {k[3:]: v for k, v in row_dict.items() if k.startswith('eh_') and v is not None}
        new_head_row_dict = {k[3:]: v for k, v in row_dict.items() if k.startswith('nh_') and v is not None}

    except Exception as e:
        print(f"Error occurred when executing query: {e}")
        return False

    # logging.info(f'query execution took: {time.time() - qtime}')

    # dtime = time.time()
    common_keys = body_row_dict.keys() & new_head_row_dict.keys()
    for key in common_keys:
        if body_row_dict[key] != new_head_row_dict[key]:
            return False
    # logging.info(f'check dicts whether extends: {time.time() - dtime}')

    # the new hid should add something new to the old hid (count as extend)
    whether_extend =  head_row_dict.items() < new_head_row_dict.items()

    # logging.info(f'check dicts whether extends: {time.time() - dtime}')

    return whether_extend


def check_if_assignment_complete(hid: str, head_time_vars: list, head_table_name: str, con=con, cur=cur) -> int or None:
    # Construct SQL conditions for each time variable
    not_null_conditions = ' AND '.join([f"{var} IS NOT NULL AND typeof({var}) = 'integer'" for var in head_time_vars])

    check_sql = f'''select 1 from {head_table_name} 
    where aid='{hid}' AND {not_null_conditions};'''

    # print(f'check_sql - check_if_assignment_complete: {check_sql}')
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

def is_bid_complete(body_table_name: str, bid: str) -> int or None:
    select_sql = f'''select 1 from {body_table_name}
    where aid='{bid}' and matched=1;
    '''
    try:
        cur.execute(select_sql)
        row = cur.fetchone()

        return row is None
    except Exception as e:
        print(f"Error occurred when executing {select_sql}: {e}")
        return None

def construct_extensions(body_table_name: str, head_table_name: str, extension_table_name: str, r: Rule, con=con, cur=cur) -> list:
    body_attr_cols = ', '.join([f"b.{col} AS b_{col}" for col in r.body_attributes])
    body_time_var_cols = ', '.join([f"b.{col} AS b_{col}" for col in r.body_time_vars])
    existing_head_attr_cols = ', '.join([f"eh.{col} AS eh_{col}" for col in r.head_attributes])
    existing_head_time_var_cols = ', '.join([f"eh.{col} AS eh_{col}" for col in r.head_time_vars])
    new_head_attr_cols = ', '.join([f"nh.{col} AS nh_{col}" for col in r.head_attributes])
    new_head_time_var_cols = ', '.join([f"nh.{col} AS nh_{col}" for col in r.head_time_vars])

    # intersection of body_attr and head_attr, intersection of body_var and head_var
    extension_condition = ''
    for attr in r.common_attributes:
        extension_condition += f'(nh.{attr}=b.{attr} or nh.{attr} IS NULL or b.{attr} IS NULL) and (nh.{attr}=eh.{attr} or eh.{attr} IS NULL) and '
    for time_var in r.common_time_vars:
        extension_condition += f'(nh.{time_var}=b.{time_var} or nh.{time_var} is Null or b.{time_var} IS NULL) and (nh.{time_var}=eh.{time_var} or eh.{time_var} IS NULL) and '


    construct_sql = f'''select ext.bid as ebid, {body_attr_cols}, {body_time_var_cols}, 
    ext.hid as ehid, {existing_head_attr_cols}, {existing_head_time_var_cols},
    nh.aid as new_hid, {new_head_attr_cols}, {new_head_time_var_cols}
    from {extension_table_name} as ext 
    left join {body_table_name} as b on b.aid=ext.bid
    left join {head_table_name} as eh on eh.aid=ext.hid
    left join {head_table_name} as nh on {extension_condition[:-4]}
    where ext.deadline IS NOT NULL
    '''

    try:
        cur.execute(construct_sql)
        extension_rows = cur.fetchall()
        columns = [description[0] for description in cur.description]
        # Convert rows to a list of dictionaries
        result = [dict(zip(columns, row)) for row in extension_rows]
        return result

    except Exception as e:
        print(f"Error occurred when executing {construct_sql}: {e}")
        return []


def update_extension_table(body_table_name: str, head_table_name: str, extension_table_name: str, r: Rule, batch_timestamp: int):
    # for each complete body assignment (all time_var are assigned in the body_table_name)
    newly_complete_bid_rows_dicts = find_newly_complete_body_assignment(body_table=body_table_name, time_vars=r.body_time_vars, batch_timestamp=batch_timestamp)

    # total_cal_eddl_time = 0
    # total_insertion_time = 0

    for bid_row_dict in newly_complete_bid_rows_dicts:
        # add row to EXT

        # ddl_time1 = time.time()
        bid = bid_row_dict.pop('aid')
        ext_row = {'bid': bid, 'hid': None, 'deadline': extended_deadline(rule=r, time_var_assignment=bid_row_dict)}
        # ddl_time2 = time.time()
        # total_cal_eddl_time += (ddl_time2 - ddl_time1)

        # insertion_time1 = time.time()
        res = insert_row_to_table(row_dict=ext_row, table_name=extension_table_name)
        # insertion_time2 = time.time()
        # total_insertion_time += (insertion_time2 - insertion_time1)

    ######## identify first part of this function's bottleneck ################
    # logging.info(f'bottleneck::::all calculation of eddl took {total_cal_eddl_time}')
    # logging.info(f'bottleneck::::all insertion of complete bid to ext took {total_insertion_time}')

    ################## for each newly updated hid
    # extended_rows = {
    # bid: , body_attr_assignment: {attr1: , attr2:}, body_time_var_assignment: {},
    # hid: , head_attr_assignment: {}, head_time_var_assignment: {}
    # new_hid: , ...
    # }
    extended_rows = construct_extensions(body_table_name=body_table_name, head_table_name=head_table_name, extension_table_name=extension_table_name, r=r)

    ebid_complete_set = set()
    for row in extended_rows:
        # assignment_dict should have body time var assignments and new head time var assignments
        if row['ebid'] in ebid_complete_set:
            continue

        body_time_var_assignment = {}
        new_head_time_var_assignment = {}
        for key, value in row.items():
            if key != 'ebid' and key != 'ehid' and key != 'new_hid':
                index = key.find('_')
                t = key[:index]
                col = key[index + 1:]
                if t == 'b' and col in r.body_time_vars:
                    body_time_var_assignment[col] = value
                elif t =='nh' and col in r.head_time_vars:
                    new_head_time_var_assignment[col] = value

        assignment_dict = {**body_time_var_assignment, **new_head_time_var_assignment}
        passed_sat_test = sat_test(solver=r.all_gap_atoms_solver, z3_vars=r.all_gap_atoms_z3_vars,
                                   assignment_dict=assignment_dict)
        if passed_sat_test == True:
            # add row to EXT
            if all(value is not None for value in new_head_time_var_assignment.values()):
                ext_row = {'bid': row['ebid'], 'hid': row['new_hid'], 'Deadline': None}
                # mark bid row in the BA table as complete
                mark_bid_complete(body_table_name=body_table_name, bid=row['ebid'])
                ebid_complete_set.add(row['ebid'])
            else:
                # saving a sat test
                ext_row = {'bid': row['ebid'], 'hid': row['new_hid'],
                           'Deadline': extended_deadline(rule=r, time_var_assignment=assignment_dict,
                                                         passed_sat_test=passed_sat_test)}
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
    logging.info(tabulate(rows, headers=columns, tablefmt="grid"))


def orchestrator(event_folder=EVENT_FOLDER, file_path=EVENT_FILE, rules=rules, window_size=WINDOW_SIZE, con=con, cur=cur):

    rules = rule_all_gap_atom_promote_to_ert_space(all_rules=rules)
    rules = rule_build_theta(all_rules=rules)

    batch_generator = parse_batches_generator(file_path)
    logging.info(f"batch_generator created from parsing {file_path}")

    # Process each batch one at a time
    now = 0

    batch_all_processing_time_mapping = {}
    body_update_time_mapping = collections.defaultdict(list)
    head_update_time_mapping = collections.defaultdict(list)
    ext_update_time_mapping = collections.defaultdict(list)

    for batch in batch_generator:

        batch_id = batch['batch_id']
        batch_timestamp = batch['timestamp']
        batch_events = batch['events']
        logging.info('=' * 50 + f'new batch of {batch_id} :::: {batch_timestamp}' + '=' * 50)

        while now <= batch_timestamp:
            logging.info('-' * 100)
            logging.info(f'Now processing batch at timestamp {now}')
            if now == batch_timestamp:
                logging.info(f"Batch ID: {batch_id}")

            delete_old_events(batch_timestamp=now, window_size=window_size, con=con, cur=cur)
            logging.info(f"deleted old events {WINDOW_SIZE} later than the batch timestamp {now}")

            if now == batch_timestamp:
                store_time1 = time.time()
                store_events(event_batch=batch_events, batch_timestamp=now, event_folder=event_folder, window_size=window_size, cur=cur)
                print(f"Stored the batch of {batch['batch_id']}: {batch['timestamp']} to events table took {time.time() - store_time1}")

            # Record the start time
            start_time = time.time()

            deletion_list = form_deletion_set(constraints=constraints, cur=cur)
            # logging.info(f"Deletion list formed: {deletion_list}")

            # carry out deletion in the event table
            deletion_from_events(deletion_list=deletion_list, con=con, cur=cur)
            # logging.info(f"deletion from the events table completed.")

            # carry out deletion in all the BA, HA, and EXT
            Bids = deletion_from_BA(deletion_list=deletion_list, rules=rules, cur=cur)
            # logging.info(f"deletion from the all BA table completed : {Bids}")

            Hids = deletion_from_HA(deletion_list=deletion_list, rules=rules, cur=cur)
            # logging.info(f"deletion from the all HA table completed : {Hids}")

            delete_from_EXT(Bids=Bids, Hids=Hids)
            # logging.info(f"deletion from the all EXT table completed ")

            insert_internal_events_from_all_cal_rules(cal_rules=cal_rules, now=now, con=con, cur=cur)

            # print_table(table_name='events')

            logging.info(f"################ batch at time {now} processing complete, violation detection starts ####################")
            all_violations = {}
            # this doesn't count as runtime
            prepared_event_batch = get_event_batch(event_table=EVENT_TABLE, batch_timestamp=now, conn=con, cur=cur)
            logging.info(f'event_batch was prepared \n')

            for r in rules:
                # logging.info(f'updating body_assignment_{r.rule_id}')
                body_update_time1 = time.time()
                update_assignment_table(event_atoms=r.body_event_atoms, gap_atoms_solver=r.body_solver, gap_atoms_z3_vars=r.body_z3_vars,
                                        time_vars=r.body_time_vars, attributes=r.body_attributes, event_batch=prepared_event_batch,
                                        batch_timestamp=now,
                                        table_name='body_assignment_' + str(r.rule_id))
                # print_table(table_name='body_assignment_' + str(r.rule_id))
                logging.info(f'body_assignment_{r.rule_id} updating completed took {time.time() - body_update_time1} seconds')
                # if now == batch_timestamp: body_update_time_mapping[(batch_id, f'body_assignment_{r.rule_id}')].append(time.time() - body_update_time1)

                # logging.info(f'updating head_assignment_{r.rule_id}')
                head_update_time1 = time.time()
                update_assignment_table(event_atoms=r.head_event_atoms, gap_atoms_solver=r.head_solver, gap_atoms_z3_vars=r.head_z3_vars,
                                        time_vars=r.head_time_vars, attributes=r.head_attributes, event_batch=prepared_event_batch,
                                        batch_timestamp=now,
                                        table_name='head_assignment_' + str(r.rule_id))
                # print_table(table_name='head_assignment_' + str(r.rule_id))
                logging.info(f'head_assignment_{r.rule_id} updating completed took {time.time() - head_update_time1} seconds')
                # if now == batch_timestamp: head_update_time_mapping[(batch_id, f'head_assignment_{r.rule_id}')].append(time.time() - head_update_time1)

                # logging.info(f'updating extension_{r.rule_id}')
                ext_update_time1 = time.time()
                update_extension_table(body_table_name='body_assignment_' + str(r.rule_id),
                                       head_table_name='head_assignment_' + str(r.rule_id),
                                       extension_table_name='extension_' + str(r.rule_id), r=r, batch_timestamp=now)
                # print_table(table_name='extension_' + str(r.rule_id))
                logging.info(f'extension_{r.rule_id} updating completed took {time.time() - ext_update_time1} seconds')
                # if now == batch_timestamp: ext_update_time_mapping[(batch_id, f'extension_{r.rule_id}')].append(time.time() - ext_update_time1)

                violations_of_this_rule = detect(extension_table_name='extension_' + str(r.rule_id), batch_timestamp=now)
                all_violations.update(violations_of_this_rule)

            # logging.info(f"violation at timestamp {now}: {all_violations}")

            # Record the end time
            end_time = time.time()
            # Calculate the elapsed time
            elapsed_time = end_time - start_time

            logging.info(f'{now} completed in {elapsed_time} seconds')
            if now == batch_timestamp:
                logging.info(f'{batch_id} :::: {batch_timestamp} completed in {elapsed_time} seconds!')
                batch_all_processing_time_mapping[batch_id] = elapsed_time
            if elapsed_time > 2:
                print(f'!!!!')
            for r in rules:
                # print('cleaning up')
                # Max time_var of body and head assignments earlier than window_size, and matched; we can clean up the body assignment and the ext assignment
                cleanup(r=r, window_size=WINDOW_SIZE, now=now, con=con, cur=cur)

            now += 1

    logging.info(':' * 50 + 'SUMMARY' + ':' * 50)
    logging.info(batch_all_processing_time_mapping)
    logging.info(body_update_time_mapping)
    logging.info(head_update_time_mapping)
    logging.info(ext_update_time_mapping)
