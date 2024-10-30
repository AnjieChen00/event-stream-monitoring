# Yacc example

import ply.yacc as yacc

# Get the token map from the lexer.  This is required.
from rulelex import tokens

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
        p[0].extend(p[3][:])

def p_rule(p):
    '''rule	:	calcrule
		| 	brule'''
    p[0] = p[1]

def p_calcrule(p):
    '''calcrule	: 	ID COLON ID LPAREN labels SEMICOLON ID EQ aggf LPAREN ID RPAREN RPAREN BA ID LPAREN labels SEMICOLON ID RPAREN AT ID IN wtype LPAREN ID COMMA NUMBER RPAREN wm'''
    p[0] = {}
    p[0]["rule_id"] = p[1] 
    p[0]["internal_event_type_name"] = p[3]
    p[0]["head_labels"] = p[5]
    p[0]["aggregated_metric_name"] = p[7]
    p[0]["aggregation_function"] = p[9]
    p[0]["metric_name"] = p[11]
    p[0]["body_function"] = p[15]
    p[0]["body_labels"] = p[17]
    p[0]["body_name"] = p[19]
    p[0]["window_type"] = p[24]
    p[0]["window_end"] = p[26]
    p[0]["window_length"] = p[28]
    p[0]["window_modulus"] = p[30]

def p_aggf(p):
    '''aggf	: 	SUM
		| 	MAX
		| 	MIN
		|	COUNT
		|	COUNTU
		|	AVG
		|	STDEV'''
    p[0] = p[1]

def p_wtype(p):
    '''wtype	: 	TUMBLING
		| 	SLIDING'''
    p[0] = p[1]

def p_wm(p):
    '''wm	: 	ID MOD NUMBER EQ NUMBER
		| 	empty'''
    p[0] = {}
    if len(p) > 2:
        p[0]["window_type"] = p[1]
        p[0]["window_end"] = p[3]
        p[0]["window_length"] = p[5]

def p_brule(p):
    'brule		: 	ID COLON LPAREN iexts RPAREN FA LPAREN aexts RPAREN'
    p[0] = {}
    p[0]["id"] = p[1]
    p[0]["body"] = p[4]
    p[0]["head"] = p[8]

def p_iid(p):
    '''iid	: 	INTERNAL
		| 	empty'''
    p[0] = p[1]

def p_theta(p):
    '''theta	: 	GT
		|	LT
		|	EQ
		| 	GTE
		|	LTE'''
    p[0] = p[1]

def p_lhs(p):
    '''lhs	: 	ID pm ID'''
    p[0] = {}
    if (p[2] == '+'):
        p[0]["coefficient_vector"] = [1,1]
    else:
        p[0]["coefficient_vector"] = [1,-1]
    p[0]["variables"] = [p[1],p[3]]

def p_pm(p):
    '''pm	: 	PLUS
		| 	MINUS'''
    p[0] = p[1]

def p_iexts(p):
    '''iexts	: 	iext COMMA iexts
		| 	iext'''
    p[0] = []
    p[0].append(p[1])
    if len(p) > 2:
        p[0].extend(p[3][:])

def p_iext(p):
    'iext	: 	iid ID LPAREN labels RPAREN AT ID' 
    p[0] = {}
    if len(p) > 2:
        p[0]["body_id"] = p[1]
        p[0]["name"] = p[2]
        p[0]["labels"] = p[4]
        p[0]["zid"] = p[7]

def p_aexts(p):
    '''aexts	: 	aext COMMA aexts
		| 	aext'''
    p[0] = []
    p[0].append(p[1])
    if len(p) > 2:
        p[o].extend(p[3][:]) 

def p_aext(p):
    'aext	: 	lhs theta NUMBER'
    p[0] = {}
    p[0]["left_hand_side"] = p[1]
    p[0]["comparative_operator"] = p[2]
    p[0]["right_constant"] = p[3]

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
# Calculation Rule
S1: calcsum(a1, a2; ax=SUM(x)) <-
eva(a1, a2; x)@z IN SLIDING (s, 5),
# Business Rule
R1: (RentBike(Bid, Cid)@x, ReturnBike(Bid, Cid)@y) -> 
(x - y <= 24)
'''
result = parser.parse(s)
print(result)
