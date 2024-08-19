class EventType:
    def __init__(self, event_type_name: str, event_report_time_granularity: int,
                 event_report_time_no_skipping: bool, event_report_time_no_skipping_granularity: str,
                 max_delay_scope: str, attribute_names: set, attributes: dict, unique: set):
        self.event_type_name = event_type_name

        self.event_report_time_granularity = event_report_time_granularity
        self.event_report_time_no_skipping = event_report_time_no_skipping

        # check if event_report_time_no_skipping is False then event_report_time_no_skipping_granularity must be "NA"
        self.event_report_time_no_skipping_granularity = event_report_time_no_skipping_granularity
        self.max_delay_scope=max_delay_scope

        # check if all the attribute_names == attributes.keys
        self.attribute_names = attribute_names
        self.attributes = attributes

        self.unique = unique

    def print_event_type(self):
        return

event_stream = [
    EventType("RentBike", 1, False, "NA",
              5,  attribute_names=set(["Bid", "Cid"]),  attributes={"Bid": str, "Cid": str}, unique=set(["Bid", "Cid", "event_time"])),
    EventType("ReturnBike", 1, False, "NA",
              5,  attribute_names=set(["Bid", "Cid"]), attributes={"Bid": str, "Cid": str}, unique=set(["Bid", "Cid", "event_time"]))
]

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
        # check if omparative_keyword is either "EARLIER" or "LATER"
        self.omparative_keyword = comparative_keyword
        self.min_count, self.max_count = min_delay, max_delay

        self.head_event_label =  head_event_label
        # check head_event_type_name is in event stream definition
        self. head_event_type_name = head_event_type_name
        # check attributes_1.keys() is a subset of attribute_names
        # check attributes_2.keys() attributes_2.keys() relations? equal or inclusive?
        self.head_attributes = head_attributes

        # in the format of {(violation_type, (event_label_1, event_label_2)): handling, ...}
        self.violation_handling = violation_handling

    def print_head(self):
        return

    def print_body(self):
        return


c1 = Constraint("a1", "RentBike", {"Bid": "x", "Cid": "y"}, 
                1, 1440, "LATER", 1, 1, 
                "b1", "ReturnBike", {"Bid": "x", "Cid": "y"},
                violation_handling={("TIME UNDER", ("a1", "b1")): "DELETE a1 b1",
                                    # ("TIME OVER", ("a1", "b1")): "DELETE a1 b1",
                                    ("COUNT OVER", ("b1")): "DELETE b1",
                                    # ("COUNT UNDER", ("b1")): "WAIT"
                                    })
# for this case, it seems that "TIME OVER" and "COUNT UNDER" is overlapping, and may be of business interest         