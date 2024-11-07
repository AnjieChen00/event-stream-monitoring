from sys_init import *
from definitions import *
from violation_detection import *

create_event_table()
create_assignment_database(rules=rules)
print("System initialization completed! ")

violations = orchestrator()

print(violations)
print("=" * 50 + "violation detection complete" + '='* 50)

con.close()