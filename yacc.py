# Yacc example

import ply.yacc as yacc

# Get the token map from the lexer.  This is required.
from constraintlex import tokens

start = 'rules'

def p_empty(p):
    'empty :'
    pass

def p_rules(p):
    '''rules	: 	rule COMMA rules
		| 	rule'''
    p[0] = []
    p[0].append(p[1])
    if len(p) > 2:
        p[0].append(p[3])

def p_rule(p):
    'rule	:	IF event THEN timedelay relationop countdelay event handles'
    p[0] = {}
    p[0]["e1"] = p[2]
    p[0]["e2"] = p[7]
    p[0]["ro"] = p[5]
    p[0]["td"] = p[4]
    p[0]["cd"] = p[6]
    p[0]["hd"] = p[8]

def p_event(p):
    'event	: 	ID COLON ID LPAREN vpairs RPAREN'
    p[0] = {}
    p[0]["tag"] = p[1]
    p[0]["name"] = p[3]
    p[0]["vp"] = p[5]

def p_vpairs(p):
    '''vpairs	: 	vpair COMMA vpairs
		|	vpair'''
    p[0] = []
    p[0].append(p[1])
    if len(p) > 2:
        p[0].append(p[3])

def p_vpair(p):
    'vpair	: 	ID COLON ID'
    p[0] = (p[1],p[3])

def p_timedelay(p):
    'timedelay	: 	mindelay maxdelay'
    p[0] = (p[1],p[2])

def p_countdelay(p):
    'countdelay	: 	mindelay maxdelay'
    p[0] = (p[1],p[2])

def p_mindelay(p):
    '''mindelay	: 	MIN NUMBER
		|	empty'''
    if len(p) > 2:
        p[0] = p[2]
    else:
        p[0] = -float('inf')

def p_maxdelay(p):
    '''maxdelay	:	MAX NUMBER
		| 	empty'''
    if len(p) > 2:
        p[0] = p[2]
    else:
        p[0] = float('inf')

def p_relationop(p):
    '''relationop	: 	EARLIER
			|	LATER
			| 	EXIST'''
    if p[1]:
        p[0] = str(p[1])

def p_handles(p):
    '''handles	: 	handle handles
		|	handle'''
    p[0] = []
    p[0].append(p[1])
    if len(p) > 2:
        p[0].append(p[2])

def p_handle(p):
    'handle	: 	CASE vtype action LPAREN labels RPAREN'
    p[0] = {}
    p[0]["vt"] = p[2]
    p[0]["act"] = p[3]
    p[0]["lbs"] = p[5]

def p_vtype(p):
    'vtype	: 	v1 v2'
    p[0] = f'{p[1]} {p[2]}'

def p_v1(p):
    '''v1	: 	TIME
		| 	COUNT'''
    p[0] = str(p[1])

def p_v2(p):
    '''v2 	: 	UNDER
		| 	OVER'''
    p[0] = str(p[1])

def p_action(p):
    '''action	: 	DELETE
		| 	GENERATE'''
    p[0] = str(p[1])

def p_labels(p):
    '''labels	: 	ID COMMA labels
		| 	ID'''
    p[0] = []
    p[0].append(p[1])
    if len(p) > 2:
        p[0].append(p[3])

# Error rule for syntax errors
def p_error(p):
    print(f"{p} Syntax error in input!")

# Build the parser
parser = yacc.yacc()

s = '''
IF r1:RentBike(cid:x,bid:y) #This is a comment
THEN LATER MIN 1 MAX 1 r2:ReturnBike(cid:x,bid:y) #This is a comment
CASE TIME OVER DELETE (r1)
CASE COUNT UNDER DELETE (r2)
	'''
result = parser.parse(s)
print(result)
