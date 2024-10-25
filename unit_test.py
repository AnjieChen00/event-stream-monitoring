import pytest
import z3

from definitions import *
from helper import *
from batch_processing import *
from violation_detection import remove_attribute_vars_from_gap_atoms, deadline, extended_deadline
from z3 import *
from violation_detection import *

# How to run 'pytest -s -p no:warnings'

## TODO: NEED TO FORMAT TESTS FOR SYS INIT AND BATCH PROCESSING

@pytest.mark.skip(reason='')
def test_1():
    atom1 = ArithmeticAtom(variables=["y", "x"], coefficient_vector=[1, -1], comparative_operator="<=", right_constant=24)
    atom2 = ArithmeticAtom(variables=["x"], coefficient_vector=[1], comparative_operator="<=", right_constant=10)

    add_result = inequality_add(atom=atom1, atom_2=atom2)
    print(add_result)

@pytest.mark.skip(reason='')
def test_2_0():
    atom3 = ArithmeticAtom(variables=["x", "y"], coefficient_vector=[1, -1], comparative_operator="<=",
                           right_constant=-2)
    atom4 = ArithmeticAtom(variables=["y", "z"], coefficient_vector=[1, -1], comparative_operator="<=",
                           right_constant=-3)
    atom5 = ArithmeticAtom(variables=["x", "z"], coefficient_vector=[1, -1], comparative_operator="<=",
                           right_constant=1)
    eliminate_res = eliminate_var(var="y", atoms=[atom3, atom4, atom5])
    for each in eliminate_res:
        print(f'result: {each}')

@pytest.mark.skip(reason='')
def test_2_1():
    atom3 = ArithmeticAtom(variables=["x", "y"], coefficient_vector=[1, -1], comparative_operator="<=",
                           right_constant=-2)
    atom4 = ArithmeticAtom(variables=["y", "z"], coefficient_vector=[-1, 1], comparative_operator=">",
                           right_constant=-3)
    atom5 = ArithmeticAtom(variables=["x", "z"], coefficient_vector=[-1, 1], comparative_operator=">",
                           right_constant=1)
    eliminate_res = eliminate_var(var="y", atoms=[atom3, atom4, atom5])
    for each in eliminate_res:
        print(f'result: {each}')

@pytest.mark.skip(reason='')
def test_2_2():
    atom3 = ArithmeticAtom(variables=["a", "b"], coefficient_vector=[1, -1], comparative_operator="<=",
                           right_constant=-1)
    atom4 = ArithmeticAtom(variables=["b", "x"], coefficient_vector=[1, -1], comparative_operator="<=",
                           right_constant=2)
    atom5 = ArithmeticAtom(variables=["a", "y"], coefficient_vector=[1, -1], comparative_operator="<=",
                           right_constant=-2)
    eliminate_res = eliminate_var(var="a", atoms=[atom3, atom4, atom5])
    for each in eliminate_res:
        print(f'step a result: {each}')
    final_res = eliminate_var(var="b", atoms=eliminate_res)
    for each in final_res:
        print(f'step b result: {each}')


@pytest.mark.skip(reason='')
def test_3():
    atom1 = ArithmeticAtom(variables=["y", "x"], coefficient_vector=[1, -1], comparative_operator=">",
                           right_constant=24)
    print(inequality_formatter(atom=atom1))

@pytest.mark.skip(reason='')
def test_4():
    r = Rule(rule_id=1, body=[EventAtom(predicate='SubmitRequest', attributes=['email', 'os'], timestamp_variable='z')],
             head=[EventAtom(predicate='DeptConfirm', attributes=['email', 'pe'], timestamp_variable='z_prime'),
                   ArithmeticAtom(variables=['pe', 'os'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=0),
                   ArithmeticAtom(variables=['os', 'pe'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=60),
                   ArithmeticAtom(variables=['pe', 'z'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=90),
                   ArithmeticAtom(variables=['z', 'pe'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=60),
                   ArithmeticAtom(variables=['z', 'z_prime'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=0),
                   ArithmeticAtom(variables=['z_prime', 'pe'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=60)])
    r1 = remove_attribute_vars_from_gap_atoms(r=r)
    print(r1)

@pytest.mark.skip(reason='')
def test_5():
    res = sat_test(arithmetic_atoms=[ArithmeticAtom(variables=['x', 'y'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=7)],
             assignment_dict={'y': 7, 'x': 15})
    print(res)


@pytest.mark.skip(reason='')
def test_z3():
    x = Int('x')
    y = Int('y')
    s = Solver()
    s.add(x > 0)
    s.add(y > 0)
    s.add(1*x + (-1)* y <= 7)
    s.add(y == 7)
    print(s.check())

@pytest.mark.skip(reason='')
def test_deadline():
    gap_atoms = [ArithmeticAtom(variables=['x', 'y'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=0),
                   ArithmeticAtom(variables=['y', 'x'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=7),
                   ArithmeticAtom(variables=['y', 'z'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=0),
                   ArithmeticAtom(variables=['z', 'y'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=7),
                   ArithmeticAtom(variables=['y', 'w'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=0),
                   ArithmeticAtom(variables=['w', 'y'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=3),
                 ArithmeticAtom(variables=['z', 'v'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=0),
                 ArithmeticAtom(variables=['v', 'z'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=7),
                 ArithmeticAtom(variables=['v', 'w'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=4),]

    # time_var_assignment = {'x': 3, 'y': 6, 'z': 8}
    time_var_assignment = {'x': 3, 'y': 6, 'z': 8, 'w': 9}

    ddl = deadline(gap_atoms=gap_atoms, time_var_assignment=time_var_assignment)
    print(ddl)

@pytest.mark.skip(reason='')
def test_extended_deadline():
    rule = Rule(rule_id=12, body=[EventAtom(predicate='Pay', attributes=['u', 'amount'], timestamp_variable='x')],
                head=[EventAtom(predicate='Schedule', attributes=['u'], timestamp_variable='y'),
                      ArithmeticAtom(variables=['x', 'y'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=-1),
                      ArithmeticAtom(variables=['y', 'x'], coefficient_vector=[1, -1], comparative_operator='<=', right_constant=2)])
    time_var_assignment = {'x': 1}
    ext_ddl = extended_deadline(rule=rule, time_var_assignment=time_var_assignment)
    print(ext_ddl)

# @pytest.mark.skip()
def test_batch_gen():
    # Example usage
    file_path = 'new.txt'
    batch_generator = parse_batches_generator(file_path)

    # Process each batch one at a time
    for batch in batch_generator:
        print(f"Batch ID: {batch['batch_id']}, Timestamp: {batch['timestamp']}")
        for event in batch['events']:
            print(event)  # Print the event dictionary
        print("END\n")

@pytest.mark.skip(reason='')
def test_store_event():
    # Example usage
    file_path = 'new.txt'
    batch_generator = parse_batches_generator(file_path)

    # Process each batch one at a time
    for batch in batch_generator:
        # print(f"Batch ID: {batch['batch_id']}, Timestamp: {batch['timestamp']}")
        store_events(batch=batch)
        print("END\n")

@pytest.mark.skip(reason='')
def test_get_batch():
    batch = get_event_batch(event_table=EVENT_TABLE, batch_timestamp=1725741350, conn=con, cur=cur)
    print(batch)

@pytest.mark.skip(reason='')
def test_get_aid():
    aid = get_next_aid(table_name='events', cur=cur, con=con)
    print(aid)

@pytest.mark.skip(reason='')
def test_insert_row():
    res = insert_row_to_table(table_name='events',
                                   row_dict={'event_report_time': 1725741351, 'event_type_name': 'RentBike', 'Bid': '23710', 'Cid': '132825199', 'event_time': 1725741350, 'event_id': '23710_132825199_1725741350'})
    print(res)
    aid = get_next_aid(table_name='events', cur=cur, con=con)
    print(aid)

@pytest.mark.skip(reason='')
def test_init_1():
    c1 = Constraint(body_event_label="a1", body_event_type_name="RentBike", body_attributes={"Bid": "x", "Cid": "y"},
                    min_delay=1, max_delay=None, comparative_keyword="LATER", min_count=1, max_count=1,
                    head_event_label="b1", head_event_type_name="ReturnBike", head_attributes={"Bid": "x", "Cid": "y"},
                    violation_handling={("TIME UNDER", ("a1", "b1")): "DELETE a1 b1",
                                        # ("TIME OVER", ("a1", "b1")): "DELETE a1 b1",
                                        ("COUNT OVER", ("b1")): "DELETE b1",
                                        # ("COUNT UNDER", ("b1")): "WAIT"
                                        })

@pytest.mark.skip(reason='')
def test_init_2():
    # just an example to test
    r = Rule(rule_id=1,
             body=[EventAtom("RentBike", attributes=["Bid", "Cid"], timestamp_variable="x")],
             head=[EventAtom("RentBike", attributes=["Bid", "Cid"], timestamp_variable="y"),
                   ArithmeticAtom(variables=["y", "x"], coefficient_vector=[1, -1], comparative_operator="<=",
                                  right_constant=24)])

    rules = [r]

    create_event_table()

    # queries = constraint_translation(c=c1)
    # # sanity checking
    # for violation, query in queries.items():
    #     print(query)
    #     try:
    #         cursor.execute(query)
    #     except sqlite3.Error as e:
    #         print(f"Error: {e}")

    create_assignment_database(rules=rules)
    conn.close()