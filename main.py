from sys_init import *
from definitions import *
from violation_detection import *

create_event_table()
create_assignment_database(rules=rules)

violations = orchestrator()

print(violations)

