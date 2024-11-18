# Yacc example

import ply.yacc as yacc

# Get the token map from the lexer.  This is required.
from definitionlex import tokens

start = 'rules'

def p_rules(p):
    '''rules    :       rule COMMA rules
                |       rule'''
    p[0] = []
    p[0].append(p[1])
    if len(p) > 2:
        p[0].extend(p[3][:])

def p_rule(p):
    'rule	:	CREATE EVENTTYPE ID LPAREN ERT NUMBER gbool NUMBER MAXDELAY NUMBER LPAREN vpairs RPAREN UNIQUE LPAREN labels RPAREN RPAREN'
    p[0] = {}
    p[0]["event_type_name"] = p[3]
    p[0]["event_report_time_granularity"] = p[6]
    p[0]["event_report_time_no_skipping"] = p[7]
    p[0]["event_report_time_no_skipping_granularity"] = p[8]
    p[0]["max_delay_scope"] = p[10]
    p[0]["attributes"] = p[12]
    p[0]["unique"] = p[16] 

def p_gbool(p):
    '''gbool	: 	SKIPPING NUMBER
		| 	NOSKIPPING'''
    if p[1] == "SKIPPING":
        p[0] = p[2]
    else:
        p[0] = None

def p_vpairs(p):
    '''vpairs	: 	vpair COMMA vpairs
		|	vpair'''  
    p[0] = []
    p[0].append(p[1])
    if len(p) > 2:
        p[0].extend(p[3][:])

def p_vpair(p):
    'vpair	: 	ID COLON ID'
    p[0] = (p[1],p[3])


def p_labels(p):
    '''labels	: 	ID COMMA labels
		| 	ID'''
    p[0] = []
    p[0].append(p[1])
    if len(p) > 2:
        p[0].extend(p[3][:])

# Error rule for syntax errors
def p_error(p):
    print(f"{p} Syntax error in input!")

# Build the parser
parser = yacc.yacc()

s = '''
CREATE EVENTTYPE RentBike (
ERT 1 NOSKIPPING 1
MAXDELAY 5
(Bid:str, Cid:str)
UNIQUE (Bid, Cid, event_time))
'''
result = parser.parse(s)
print(result)
