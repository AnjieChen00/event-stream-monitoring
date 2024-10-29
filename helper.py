import copy
import sqlite3
from z3 import *

from definitions import *


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
        conn.row_factory = sqlite3.Row
        return conn

con = connect_sqlite_db()
cur = con.cursor()

def build_theta(arithmetic_atoms: list[ArithmeticAtom], assignment_dict: dict) -> Solver:
    # Create a Z3 solver instance
    solver = Solver()

    # Create a mapping of variables to Z3 Real types
    z3_vars = {}
    for atom in arithmetic_atoms:
        for var in atom.variables:
            if var not in z3_vars:
                z3_vars[var] = Int(var)
                solver.add(z3_vars[var] > 0)

    # Add constraints to the solver
    for atom in arithmetic_atoms:
        # Build the linear expression from the atom
        # Initialize an empty expression
        expr = 0

        # Build the expression term by term
        for coef, var in zip(atom.coefficient_vector, atom.variables):
            expr += coef * z3_vars[var]
        # print(f'expression on the left side: {expr}')

        # Apply the comparative operator and add to the solver
        if atom.comparative_operator == '<=':
            solver.add(expr <= atom.right_constant)
        elif atom.comparative_operator == '>=':
            solver.add(expr >= atom.right_constant)
        elif atom.comparative_operator == '<':
            solver.add(expr < atom.right_constant)
        elif atom.comparative_operator == '>':
            solver.add(expr > atom.right_constant)
        elif atom.comparative_operator == '=':
            solver.add(expr == atom.right_constant)
        else:
            raise ValueError(f"Unsupported operator: {atom.comparative_operator}")

    # Substitute the known values from the assignment dictionary
    for var, value in assignment_dict.items():
        if var in z3_vars:
            solver.add(z3_vars[var] == value)

    # # Print the constraints in the solver
    # print("Constraints in the current solver:")
    # for constraint in solver.assertions():
    #     print(constraint)

    return solver

def sat_test(arithmetic_atoms: list[ArithmeticAtom], assignment_dict: dict) -> int:
    '''
    Evaluates whether the set of inequalities is satisfiable given partial assignments.
    :param arithmetic_atoms: List of inequalities in the form of ArithmeticAtom objects.
    :param assignment_dict: Dictionary of variable assignments in the format {var: value}.
    :return: True if the system is satisfiable, False otherwise.
    '''
    solver = build_theta(arithmetic_atoms, assignment_dict)
    res = solver.check()
    print(f'Sat test result: {res}')

    # Check for satisfiability
    if res == z3.sat:
        return True
    else:
        return False


def parse_row_to_dict(row: str) -> dict:
    '''
    parse a row string like "key: value, key: value" to a dict
    '''
    items = row.split(',')
    d = {}
    for items in items:
        key, value = items.split(':')
        d[key] = value
    return d

def fetch_type_definition_from_stream_definition(event_type_name: str) -> EventType or None:
    for defi in event_stream:
        if defi.event_type_name == event_type_name:
            return defi
    return None

def execute_insertion(table_name: str, columns: str, values: str):
    '''
    table_name should a string
    columns and values should be strings where fields are separated by commas
    '''
    sql = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"
    print(f'insertion sql: {sql}')

    try:
        cur.execute(sql)
        con.commit()
    except sqlite3.Error as e:
        print(f"Error: {e}")

def inequality_formatter(atom: ArithmeticAtom) -> ArithmeticAtom:
    if atom.comparative_operator == '>=':
        atom.coefficient_vector = [(-1)* c for c in atom.coefficient_vector]
        atom.right_constant = (-1) * atom.right_constant
        atom.comparative_operator = '<='
        return atom
    elif atom.comparative_operator == '>':
        atom.coefficient_vector = [(-1)* c for c in atom.coefficient_vector]
        atom.right_constant = (-1) * atom.right_constant
        atom.comparative_operator = '<'
        return atom
    else:
        return atom


def inequality_add(atom: ArithmeticAtom, atom_2: ArithmeticAtom) -> ArithmeticAtom or None:
    all_existing_vars = list(set(atom.variables + atom_2.variables))

    if atom.comparative_operator == '=' and atom_2.comparative_operator == '=':
        result_op = '='
    elif atom.comparative_operator == '<'  or atom_2.comparative_operator == '<' :
        result_op = '<'
    else:
        result_op = '<='

    result_covector = []
    for v in all_existing_vars:
        if v in atom.variables:
            index_of_v = atom.variables.index(v)
            coefficient_of_v = atom.coefficient_vector[index_of_v]
        else:
            coefficient_of_v = 0

        if v in atom_2.variables:
            index_of_v_2 = atom_2.variables.index(v)
            coefficient_of_v_2 = atom_2.coefficient_vector[index_of_v_2]
        else:
            coefficient_of_v_2 = 0

        result_covector.append(coefficient_of_v + coefficient_of_v_2)

    # delete item whose coefficient is 0
    index_to_delete = []
    for i, (var, co) in enumerate(zip(all_existing_vars, result_covector)):
        if co == 0:
            index_to_delete.append(i)
    final_result_vars, final_result_covector = [], []
    for i, (var, co) in enumerate(zip(all_existing_vars, result_covector)):
        if i not in index_to_delete:
            final_result_vars.append(var)
            final_result_covector.append(co)

    if len(final_result_vars) == 0 and len(final_result_covector) == 0:
        print(f'result after inequality add of {atom} and {atom_2} is None')
        return None

    result = ArithmeticAtom(variables=final_result_vars, coefficient_vector=final_result_covector, comparative_operator=result_op,
                            right_constant=atom.right_constant + atom_2.right_constant)

    print(f'result after inequality add of {atom} and {atom_2} is {result}')

    return result

def simplify_inequalities(inequalities: list[ArithmeticAtom]) -> list[ArithmeticAtom]:
    '''
    operators should be formatted already <=, < or ==
    should be done last
    '''
    print('inequalities: ' + ', '.join(str(x) for x in inequalities))

    res = []
    for i in range(len(inequalities)):
        e1 = inequalities[i]
        ignore = False
        for j in range(len(inequalities)):
            if j == i:
                continue
            e2 = inequalities[j]
            print(f'comparing {e1} and {e2}')

            same = True
            if set(e1.variables) == set(e2.variables) and e1.comparative_operator == e2.comparative_operator:
                for index in range(len(e1.variables)):
                    jndex = e2.variables.index(e1.variables[index])
                    if e1.coefficient_vector[index] != e2.coefficient_vector[jndex]:
                        same = False
                        break

                if same and e1.right_constant >= e2.right_constant:
                    # ignore e1
                    ignore = True
        if not ignore:
            res.append(e1)
    return res


def eliminate_var(var: str, atoms: list[ArithmeticAtom]) -> list[ArithmeticAtom]:
    '''
    eliminate var from atoms;
    atoms are formatted using format_factory: comparative_operator <=, < or =
    '''
    # format atoms
    for i in range(len(atoms)):
        atoms[i] = inequality_formatter(atoms[i])

    # eliminate var as follows
    without_var = []
    new_atoms = []

    # Step 1: for each atom (inequality), if the coefficient of var is c which is not 0, multiply the inequality by 1/c
    positive = False
    negative = False
    something_to_eliminate = False
    for atom in atoms:
        # print(f'processing atom: {atom}')
        if var in atom.variables:
            something_to_eliminate = True
            index_of_var = atom.variables.index(var)
            coefficient_of_var = atom.coefficient_vector[index_of_var]
            if coefficient_of_var != 0:
                if coefficient_of_var < 0:
                    new_coefficient_vector = [c/(-coefficient_of_var) for c in atom.coefficient_vector]
                    new_atom = ArithmeticAtom(variables=atom.variables, coefficient_vector=new_coefficient_vector,
                                              comparative_operator=atom.comparative_operator,
                                              right_constant=atom.right_constant / (-coefficient_of_var))
                else:
                    new_coefficient_vector = [c / coefficient_of_var for c in atom.coefficient_vector]
                    new_atom = ArithmeticAtom(variables=atom.variables, coefficient_vector=new_coefficient_vector,
                                              comparative_operator=atom.comparative_operator, right_constant=atom.right_constant/coefficient_of_var)

                # print(atom.variables, new_coefficient_vector)

                # as a result from Step 1, we have a new system of inequalities
                if new_atom.coefficient_vector[index_of_var] == 1:
                    positive = True
                    # print('coefficient of var is 1')
                elif new_atom.coefficient_vector[index_of_var] == -1:
                    negative = True
                    # print('coefficient of var is -1')
                new_atoms.append(new_atom)
                # print(f'new_atom from division: {new_atom}')
        else:
            without_var.append(atom)

    # Step 2. make sure there is at least one +1 and one -1 as coefficient for var in new_atoms. If not, cannot do elimination
    if something_to_eliminate:
        if (not positive and negative) or (positive and not negative):
            print(f'Unable to do the elimination for {var}')

    # Step 3: for each inequality in which the coefficient of var is positive and for each inequality in which the coefficient of var is negative,
    # add them to obtain a new inequality
    result = set()
    for i in range(len(new_atoms)):
        new_atom = new_atoms[i]
        index_of_var = new_atom.variables.index(var)
        coefficient_of_var = new_atom.coefficient_vector[index_of_var]
        if coefficient_of_var == 1:
            for j in range(i + 1, len(new_atoms)):
                new_atom_2 =  new_atoms[j]
                index_of_var_2 = new_atom_2.variables.index(var)
                coefficient_of_var_2 = new_atom_2.coefficient_vector[index_of_var_2]
                if coefficient_of_var_2 == 1:
                    continue
                elif coefficient_of_var_2 == -1:
                    # perform inequality add
                    # print(f'performing inequality add: {new_atom}, {new_atom_2}')
                    new_inequality = inequality_add(new_atom, new_atom_2)
                    if new_inequality: result.add(new_inequality)
        elif coefficient_of_var == -1:
            for j in range(i + 1, len(new_atoms)):
                new_atom_2 =  new_atoms[j]
                index_of_var_2 = new_atom_2.variables.index(var)
                coefficient_of_var_2 = new_atom_2.coefficient_vector[index_of_var_2]
                if coefficient_of_var_2 == -1:
                    continue
                elif coefficient_of_var_2 == 1:
                    # perform inequality add
                    new_inequality = inequality_add(new_atom, new_atom_2)
                    if new_inequality: result.add(new_inequality)
        else:
            print("Step 1 of division incorrect")

    return list(set(list(result) + without_var))


class SQL_Factory:
    def __init__(self):
        pass


def evaluate(gap_atoms: list[ArithmeticAtom], time_var_assignments: dict) -> list[ArithmeticAtom] or None:
    # if not sat_test(arithmetic_atoms=gap_atoms, time_var_assignments=time_var_assignments):
    #     print()
    #     return None
    # for gap_atom in gap_atoms:
    #     var1, var2 = gap_atom.variables
    #     if var1 in time_var_assignments and var
    pass

