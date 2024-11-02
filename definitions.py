import pickle
import ast

from pandocfilters import attributes
from scipy.stats import maxwell

# import numpy as np

EVENT_TABLE = 'events'
DBNAME = 'monitor.db'
WINDOW_SIZE = 864000 #10 days in unix time(presented by seconds)
EVENT_FOLDER = 'events/'
EVENT_FILE = 'budget.txt'

# some are based on sqlite3
aggregation_function_allowed=['AVG', 'COUNT', 'MAX', 'MIN', 'SUM', 'STDEV']
class EventType:
    def __init__(self, event_type_name: str,
                 event_time_granularity: int,
                 event_time_no_skipping: bool, event_time_no_skipping_granularity: int or None,
                 event_report_time_granularity: int,
                 event_report_time_no_skipping: bool, event_report_time_no_skipping_granularity: int or None,
                 max_delay_scope: int, attributes: dict, unique: set):
        self.event_type_name = event_type_name

        self.event_time_granularity = event_time_granularity
        self.event_time_no_skipping = event_time_no_skipping
        # check if event_report_time_no_skipping is False then event_report_time_no_skipping_granularity must be "NA"
        self.event_time_no_skipping_granularity = event_time_no_skipping_granularity

        self.event_report_time_granularity = event_report_time_granularity
        self.event_report_time_no_skipping = event_report_time_no_skipping
        # check if event_report_time_no_skipping is False then event_report_time_no_skipping_granularity must be "NA"
        self.event_report_time_no_skipping_granularity = event_report_time_no_skipping_granularity

        self.max_delay_scope = max_delay_scope

        self.attributes = attributes

        self.unique = unique

    def print_event_type(self):
        return


# IF body THEN head
# head: ignore current
class Constraint:
    def __init__(self, body_event_label: str, body_event_type_name: str, body_attributes: dict,
                 min_delay: int, max_delay: int, comparative_keyword: str,
                 min_count: int, max_count: int,
                 head_event_label: str, head_event_type_name: str, head_attributes: dict,
                 violation_handling: dict):
        self.body_event_label = body_event_label
        # check body_event_type_name is in event stream definition
        self.body_event_type_name = body_event_type_name
        # check body_attributes.keys() is a subset of attribute_names
        self.body_attributes = body_attributes

        self.min_delay, self.max_delay = min_delay, max_delay
        # check if comparative_keyword is either "EARLIER" or "LATER"
        self.comparative_keyword = comparative_keyword
        self.min_count, self.max_count = min_count, max_count

        self.head_event_label = head_event_label
        # check head_event_type_name is in event stream definition
        self.head_event_type_name = head_event_type_name
        # check attributes_1.keys() is a subset of attribute_names
        # check attributes_2.keys() attributes_2.keys() relations? equal or inclusive?
        self.head_attributes = head_attributes

        # in the format of {(violation_type, (event_label_1, event_label_2)): handling, ...}
        self.violation_handling = violation_handling

    def print_head(self):
        return

    def print_body(self):
        return


class EventAtom:
    def __init__(self, predicate: str, attributes: list, timestamp_variable: str, metric_attribute=None,
                 aggregated_metric_attribute=None, aggregation_function=None, internal=False):
        self.predicate = predicate
        self.attributes = attributes
        self.timestamp_variable = timestamp_variable

        # only one metric value can exist
        if (not metric_attribute and aggregated_metric_attribute):
            internal = True
        elif (metric_attribute and not aggregated_metric_attribute):
            internal = False
        else:
            print("Illegal EventAtom, can only be external or internal")
        self.internal = internal

        self.metric_attribute = metric_attribute
        if metric_attribute:
            self.attributes.append(metric_attribute)

        self.aggregated_metric_attribute = aggregated_metric_attribute
        if aggregated_metric_attribute:
            self.attributes.append(aggregated_metric_attribute)
        self.attributes = list(set(self.attributes))

        if aggregation_function and aggregation_function in aggregation_function_allowed:
            self.aggregation_function = aggregation_function
            self.aggregated_metric_attribute = aggregated_metric_attribute

    def __repr__(self):
        if not self.aggregation_function:
            return self.predicate + "(" + ", ".join(self.attributes) + ")@" + self.timestamp_variable
        else:
            return f'{self.predicate} ({", ".join(self.attributes)}, {self.aggregated_metric_attribute}={self.aggregation_function}(body_metric_attribute) @{self.timestamp_variable}'


class ArithmeticAtom:
    def __init__(self, variables: list, coefficient_vector: list, comparative_operator, right_constant):
        # general format: a1*x1 + a2*x2 + ... + ai*xi <= b
        # the atom can have 0-n variables, the variables can be time vars or attribute vars
        # constants can be negative
        # Gap atom are simpler, as there would only be two variables (can be time var or attribute var)
        if len(variables) == len(coefficient_vector) and len(variables) <= 2 and len(coefficient_vector) <= 2:
            self.variables = variables
            self.coefficient_vector = coefficient_vector
            for coef in self.coefficient_vector:
                if abs(coef) != 0 and abs(coef) != 1:
                    print('This is not a gap atom !!')
        else:
            print("ArithmeticAtom parsing incorrect, variables and coefficients should be of same length and <= 2.")
        self.comparative_operator = comparative_operator
        self.right_constant = right_constant

    def __str__(self):
        atom_str = ''
        for i in range(len(self.variables)):
            atom_str += f'{self.coefficient_vector[i]} * {self.variables[i]} + '
        atom_str = atom_str[:-2]
        atom_str += f'{self.comparative_operator} {self.right_constant}'
        return atom_str


class Rule:
    def __init__(self, rule_id:int, body:list, head:list):
        # self-assigned rule_id during parsing.
        self.rule_id = rule_id

        # body and head are combinations of event atoms and arithmetic atoms

        if not all(isinstance(item, (EventAtom, ArithmeticAtom)) for item in body) or not all(isinstance(item, (EventAtom, ArithmeticAtom)) for item in head):
            raise ValueError("All elements in the body and head must be atom types")

        # all vars appeared in the body's gap atom should be in the event atoms already (parsing should check?)
        self.body = body
        self.head = head

        self.body_event_atoms = [item for item in self.body if isinstance(item, EventAtom)]
        self.body_time_vars = list(set([item.timestamp_variable for item in self.body if isinstance(item, EventAtom)]))
        self.body_attributes = list(set([attr for item in self.body if isinstance(item, EventAtom) for attr in item.attributes]))
        self.body_arithmetic_atoms = [item for item in self.body if isinstance(item, ArithmeticAtom)]

        self.head_event_atoms = [item for item in self.head if isinstance(item, EventAtom)]
        self.head_time_vars = list(set([item.timestamp_variable for item in self.head if isinstance(item, EventAtom)]))
        self.head_attributes = list(set([attr for item in self.head if isinstance(item, EventAtom) for attr in item.attributes]))
        self.head_arithmetic_atoms = [item for item in self.head if isinstance(item, ArithmeticAtom)]

    def __str__(self):
        return str(self.rule_id) + ': \n' + ", ".join(str(item) for item in self.body) + " --> " + ", ".join(str(item) for item in self.head)

class Window:
    def __init__(self, window_type: str, window_end: str, window_length: int):
        self.window_type = window_type # can only be TUMBLING or SLIDING
        self.window_end = window_end
        self.window_length = window_length
    def __str__(self):
        return f'IN {self.window_type} [{self.window_end}, {self.window_length}]'

class CalculationRule:
    def __init__(self, rule_id: int, body: list, head: list):
        self.rule_id = rule_id
        # body should only have one EventAtom and one Window type object
        if len(body) == 2:
            for obj in body:
                if isinstance(obj, Window):
                    self.window = obj
                elif isinstance(obj, EventAtom) and obj.metric_attribute:
                    self.body_event_atom = obj
                else:
                    print("Illegal object type in calculation rule body")
        else:
            print("calculation rule body length should be 2")
        self.body = body

        # head can only have EventAtom type objects and the source event's metric_attribute should be present in body's attributes
        for event_atom in head:
            if not isinstance(event_atom, EventAtom):
                print(f"calculation rule {rule_id} head illegal")
            if self.window.window_end not in event_atom.timestamp_variable:
                # window end is s, then internal event ts should be s + n (n=0,...)
                print(f"calculation rule {rule_id} head's timestamp variable illegal")
        self.head = head

    def __str__(self):
        return str(self.rule_id) + ': \n' + ", ".join(str(item) for item in self.head) + " <== " + ", ".join(str(item) for item in self.body)


############################ Output from the parsing ###########################################################
############################ bike example ######################################################################
# RentBike = EventType(event_type_name="RentBike", event_time_granularity=1, event_time_no_skipping=False, event_time_no_skipping_granularity=None,
#             event_report_time_granularity=1, event_report_time_no_skipping=False, event_report_time_no_skipping_granularity=None, max_delay_scope=3,
#             attributes={"Bid": "TEXT", "Cid": "TEXT"}, unique=set(["Bid", "Cid", "event_time"]))
#
# ReturnBike = EventType(event_type_name="ReturnBike", event_time_granularity=1, event_time_no_skipping=False, event_time_no_skipping_granularity=None,
#             event_report_time_granularity=1, event_report_time_no_skipping=False, event_report_time_no_skipping_granularity=None, max_delay_scope=3,
#             attributes={"Bid": "TEXT", "Cid": "TEXT"}, unique=set(["Bid", "Cid", "event_time"]))
# event_stream = [RentBike,ReturnBike]
# c1 = Constraint("a1", "RentBike", {"Bid": "x", "Cid": "y"},
# 				1, 1440, "LATER", 1, 1,
# 				"b1", "ReturnBike", {"Bid": "x", "Cid": "y"},
# 				violation_handling={("TIME UNDER", ("a1", "b1")): "DELETE a1 b1",
# 									# ("TIME OVER", ("a1", "b1")): "DELETE a1 b1",
# 									("COUNT OVER", ("b1")): "DELETE b1",
# 									# ("COUNT UNDER", ("b1")): "WAIT"
# 									})
# constraints = [c1]
#
# # just an example to test
# r = Rule(rule_id=1,
#          body=[EventAtom("RentBike", attributes=["Bid", "Cid"], timestamp_variable="x")],
#          head=[EventAtom("RentBike", attributes=["Bid", "Cid"], timestamp_variable="y"),
#                ArithmeticAtom(variables=["y", "x"], coefficient_vector=[1, -1], comparative_operator="<=",
#                               right_constant=24)])
#
# rules = [r]
############################################################################################################
# Pay = EventType(event_type_name="Pay", event_report_time_granularity=1, event_report_time_no_skipping=False, event_report_time_no_skipping_granularity="NA",
#                 max_delay_scope=2, attributes={'u': 'TEXT', 'amount': 'INTEGER'}, unique=set(['u', 'event_time']))
#
# Schedule = EventType(event_type_name="Schedule", event_report_time_granularity=1, event_report_time_no_skipping=False, event_report_time_no_skipping_granularity="NA",
#                 max_delay_scope=1, attributes={'u': 'TEXT'}, unique=set(['u', 'event_time']))
# event_stream = [Pay, Schedule]
############################################################################################################
# place_order = EventType(event_type_name='placeOrder',
#                         event_time_granularity=1, event_time_no_skipping=False,
#                         event_time_no_skipping_granularity=None,
#                         event_report_time_granularity=1, event_report_time_no_skipping=False,
#                         event_report_time_no_skipping_granularity=None,
#                         max_delay_scope=3,
#                         # 'item_id_quantity_mapping' string should be like {'iphone16xxyyzzz': 10, 'carpetiii0099ppp': 1}
#                         attributes={'user_id': 'TEXT', 'order_id': 'TEXT', 'item_id_quantity_mapping': 'TEXT',
#                                     'payment_method': 'TEXT', 'payment_amount': 'INTEGER',
#                                     'payment_tracking_id': 'TEXT'},
#                         unique=set(['order_id']))
#
# initiate_return = EventType(event_type_name='initReturn',
#                         event_time_granularity=1, event_time_no_skipping=False,
#                         event_time_no_skipping_granularity=None,
#                         event_report_time_granularity=1, event_report_time_no_skipping=False,
#                         event_report_time_no_skipping_granularity=None,
#                         max_delay_scope=3,
#                         # 'requested_return_item_id_quantity_mapping' string should be like {'iphone16xxyyzzz': 10, 'carpetiii0099ppp': 1}
#                         attributes={'user_id': 'TEXT', 'order_id': 'TEXT', 'requested_return_item_id_quantity_mapping': 'TEXT',
#                                     'payment_method': 'TEXT', 'payment_amount': 'INTEGER', 'payment_tracking_id': 'TEXT',
#                                     'requested_amount': 'INTEGER'
#                                     },
#                         unique=set(['order_id', 'requested_return_item_ids']))
#
# event_stream = [place_order, initiate_return]
#
# c1 = Constraint("a1", "placeOrder", {"user_id": "x", "order_id": "y"},
# 				60, 36000, "LATER", 0, 10,
# 				"b1", "ReturnBike", {"Bid": "x", "Cid": "y"},
# 				violation_handling={("TIME UNDER", ("a1", "b1")): "DELETE b1",
# 									("TIME OVER", ("a1", "b1")): "DELETE b1",
# 									("COUNT OVER", ("b1")): "DELETE b1",
# 									})
#
# ############################################################################################################
# ######################## A complete example of shipping monitoring #############################################
# place_order = EventType(event_type_name='place_order',
#                         event_time_granularity=1, event_time_no_skipping=False,
#                         event_time_no_skipping_granularity=None,
#                         event_report_time_granularity=1, event_report_time_no_skipping=False,
#                         event_report_time_no_skipping_granularity=None,
#                         max_delay_scope=3,
#                         # 'item_id_quantity_mapping' string should be like {'iphone16xxyyzzz': 10, 'carpetiii0099ppp': 1}
#                         attributes={'user_id': 'TEXT', 'order_id': 'TEXT', 'item_id_quantity_mapping': 'TEXT',
#                                     'payment_method': 'TEXT', 'payment_amount': 'INTEGER',
#                                     'payment_tracking_id': 'TEXT'},
#                         unique=set(['order_id']))
#
# picking = EventType(event_type_name='picking',
#                     event_time_granularity=1, event_time_no_skipping=False,
#                     event_time_no_skipping_granularity=None,
#                     event_report_time_granularity=1, event_report_time_no_skipping=False,
#                     event_report_time_no_skipping_granularity=None,
#                     max_delay_scope=3,
#                     attributes={'order_id': 'TEXT', 'package_id': 'TEXT', 'item_id': 'TEXT', 'warehouse_id': 'TEXT'},
#                     unique=set(['order_id', 'package_id', 'item_id', 'warehouse_id', 'event_time']))
#
# packing = EventType(event_type_name='packing',
#                     event_time_granularity=1, event_time_no_skipping=False,
#                     event_time_no_skipping_granularity=None,
#                     event_report_time_granularity=1, event_report_time_no_skipping=False,
#                     event_report_time_no_skipping_granularity=None,
#                     max_delay_scope=3,
#                     # 'item_id_quantity_mapping' string should be like {'iphone16xxyyzzz': 10, 'carpetiii0099ppp': 1}
#                     attributes={'order_id': 'TEXT', 'package_id': 'TEXT', 'item_id_quantity_mapping': 'TEXT', 'warehouse_id': 'TEXT'},
#                     unique=set(['order_id', 'package_id']))
#
# assign_carrier = EventType(event_type_name='assign_carrier',
#                     event_time_granularity=1, event_time_no_skipping=False,
#                     event_time_no_skipping_granularity=None,
#                     event_report_time_granularity=1, event_report_time_no_skipping=False,
#                     event_report_time_no_skipping_granularity=None,
#                     max_delay_scope=3,
#                     # 'item_id_quantity_mapping' string should be like {'iphone16xxyyzzz': 10, 'carpetiii0099ppp': 1}
#                     attributes={'package_id': 'TEXT', 'warehouse_id': 'TEXT', 'carrier_id': 'TEXT'},
#                     unique=set(['package_id', 'warehouse_id', 'carrier_id']))
#
# print_shipping_label = EventType(event_type_name='print_shipping_label',
#                     event_time_granularity=1, event_time_no_skipping=False,
#                     event_time_no_skipping_granularity=None,
#                     event_report_time_granularity=1, event_report_time_no_skipping=False,
#                     event_report_time_no_skipping_granularity=None,
#                     max_delay_scope=3,
#                     # 'item_id_quantity_mapping' string should be like {'iphone16xxyyzzz': 10, 'carpetiii0099ppp': 1}
#                     attributes={'package_id': 'TEXT', 'warehouse_id': 'TEXT', 'carrier_id': 'TEXT', 'tracking_number': 'TEXT'},
#                     unique=set(['tracking_number']))
#
# ship = EventType(event_type_name='ship',
#                     event_time_granularity=1, event_time_no_skipping=False,
#                     event_time_no_skipping_granularity=None,
#                     event_report_time_granularity=1, event_report_time_no_skipping=False,
#                     event_report_time_no_skipping_granularity=None,
#                     max_delay_scope=3,
#                     # 'item_id_quantity_mapping' string should be like {'iphone16xxyyzzz': 10, 'carpetiii0099ppp': 1}
#                     attributes={'package_id': 'TEXT', 'warehouse_id': 'TEXT', 'carrier_id': 'TEXT', 'tracking_number': 'TEXT'},
#                     unique=set(['tracking_number']))
#
# deliver = EventType(event_type_name='deliver',
#                     event_time_granularity=1, event_time_no_skipping=False,
#                     event_time_no_skipping_granularity=None,
#                     event_report_time_granularity=1, event_report_time_no_skipping=False,
#                     event_report_time_no_skipping_granularity=None,
#                     max_delay_scope=3,
#                     # 'item_id_quantity_mapping' string should be like {'iphone16xxyyzzz': 10, 'carpetiii0099ppp': 1}
#                     attributes={'package_id': 'TEXT', 'carrier_id': 'TEXT', 'tracking_number': 'TEXT'},
#                     unique=set(['tracking_number']))
#
# confirm_delivery = EventType(event_type_name='confirm_delivery',
#                     event_time_granularity=1, event_time_no_skipping=False,
#                     event_time_no_skipping_granularity=None,
#                     event_report_time_granularity=1, event_report_time_no_skipping=False,
#                     event_report_time_no_skipping_granularity=None,
#                     max_delay_scope=3,
#                     # 'item_id_quantity_mapping' string should be like {'iphone16xxyyzzz': 10, 'carpetiii0099ppp': 1}
#                     attributes={'package_id': 'TEXT', 'carrier_id': 'TEXT', 'tracking_number': 'TEXT'},
#                     unique=set(['tracking_number']))
#
# # there could be multiple picking that corresponds to one packing
# # one picking can only have one packing
# event_stream = [place_order, picking, packing, assign_carrier, print_shipping_label, ship, deliver, confirm_delivery]
# c1 = Constraint(body_event_label="a1", body_event_type_name="packing", body_attributes={"order_id": "x", "package_id": "y"},
#                min_delay=0, max_delay=8000, comparative_keyword="EARLIER", min_count=1, max_count=3,
#                head_event_label="b1", head_event_type_name="picking", head_attributes={"order_id": "x", "package_id": "y"},
#                violation_handling={("TIME OVER", ("a1", "b1")): "DELETE a1 b1",
#                                    ("COUNT OVER", ("b1")): "DELETE b1",})
#
# constraints = [c1]
#
# # if not picked within a day, report violation; any picking shouldn't be later than a day
# r1 = Rule(rule_id=101, body=[EventAtom(predicate='place_order', attributes=['user_id', 'order_id'], timestamp_variable='x')],
#          head=[EventAtom(predicate='picking', attributes=['order_id', 'item_id', 'warehouse_id'], timestamp_variable='y'),
#                ArithmeticAtom(variables=['x', 'y'], coefficient_vector=[-1, 1], comparative_operator='<=', right_constant=86400)])
#
# # if didn't have shipping label within a day, report violation
# r2 = Rule(rule_id=102, body=[EventAtom(predicate='place_order', attributes=['user_id', 'order_id'], timestamp_variable='x')
#     , EventAtom(predicate='packing', attributes=['order_id', 'package_id'], timestamp_variable='y')],
#          head=[EventAtom(predicate='print_shipping_label', attributes=['package_id'], timestamp_variable='z'),
#                ArithmeticAtom(variables=['x', 'z'], coefficient_vector=[-1, 1], comparative_operator='<=', right_constant=90000),
#                ArithmeticAtom(variables=['x', 'y'], coefficient_vector=[-1, 1], comparative_operator='<=', right_constant=88000),])
# rules=[r2]
#
# ############################################################################################################
################################# budget monitoring example ##################################################
item_cost = EventType(event_type_name="item_cost",
                      event_time_granularity=1, event_time_no_skipping=False, event_time_no_skipping_granularity=None,
                      event_report_time_granularity=1, event_report_time_no_skipping=False, event_report_time_no_skipping_granularity=None,
                      max_delay_scope=2, attributes={'account': 'TEXT', 'product_code': 'TEXT', 'service_tag': 'TEXT', 'timestamp_interval': 'TEXT', 'icost': 'REAL'},
                      unique=set(['account', 'product_code', 'service_tag', 'timestamp_interval', 'event_time']))
daily_cost = EventType(event_type_name="daily_cost",
                      event_time_granularity=1, event_time_no_skipping=False, event_time_no_skipping_granularity=None,
                      event_report_time_granularity=1, event_report_time_no_skipping=False, event_report_time_no_skipping_granularity=None,
                      max_delay_scope=0, attributes={'account': 'TEXT', 'product_code': 'TEXT', 'service_tag': 'TEXT', 'dcost': 'REAL'},
                      unique=set(['account', 'product_code', 'service_tag', 'event_time']))

event_stream = [item_cost, daily_cost]
cr1 = CalculationRule(rule_id=71, body=[EventAtom(predicate='item_cost', attributes=['account', 'product_code', 'service_tag', 'timestamp_interval'],
                                                  metric_attribute='icost', timestamp_variable='z'),
                                        Window(window_type='TUMBLING', window_length=10, window_end='s')],
                      head=[EventAtom(predicate='daily_cost', attributes=['account', 'product_code', 'service_tag'],
                                      timestamp_variable='s+1',
                                      aggregated_metric_attribute='dcost', aggregation_function='SUM')])

cal_rules = [cr1]
rules = []
constraints = []

############################################################################################################

all_attributes = {}
for et in event_stream:
    # all_attribute_names.update(et.attribute_names)
    all_attributes.update(et.attributes)

# print(all_attributes)




# if __name__ == "__main__":
#
#
#     # for this case, it seems that "TIME OVER" and "COUNT UNDER" is overlapping, and may be of business interest
#
#     ################################### Save event type objects to a file
#     with open('event_type_objects.pkl', 'wb') as file:
#         pickle.dump(event_stream, file)
#
#     #################################### Load objects from the file
#     with open('event_type_objects.pkl', 'rb') as file:
#         loaded_objects = pickle.load(file)
#
#     #################################### Verify the loaded objects
#     for obj in loaded_objects:
#         print(obj.event_type_name)
#
#     #################################### Save contraint objects to a file
#     with open('constraint_objects.pkl', 'wb') as cfile:
#         pickle.dump([c1], cfile)
#
#     #################################### Load objects from the file
#     with open('constraint_objects.pkl', 'rb') as cfile:
#         cobjects = pickle.load(cfile)
#
#     ################################### Verify the loaded objects
#     for obj in cobjects:
#         # print(type(obj))
#         print(obj.body_event_type_name, obj.head_event_type_name)
