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
    p[0]["id"] = p[1] 
    p[0]["iname"] = p[3]
    p[0]["labels"] = p[5]
    p[0]["amn"] = p[7]
    p[0]["aggf"] = p[9]
    p[0]["mname"] = p[11]
    p[0]["name"] = p[15]
    p[0]["labels2"] = p[17]
    p[0]["mname2"] = p[19]
    p[0]["wtype"] = p[24]
    p[0]["wend"] = p[26]
    p[0]["wlen"] = p[28]
    p[0]["wmod"] = p[30]

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
        p[0]["wtype"] = p[1]
        p[0]["wend"] = p[3]
        p[0]["wlen"] = p[5]

def p_brule(p):
    'brule		: 	ID COLON LPAREN iexts RPAREN FA LPAREN aexts RPAREN'
    p[0] = {}
    p[0]["id"] = p[1]
    p[0]["iexts"] = p[4]
    p[0]["aexts"] = p[8]

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

def p_npair(p):
    'npair	: 	ID pm NUMBER'
    p[0] = (p[1], p[2], p[3])

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
        p[0]["iid"] = p[1]
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
    'aext	: 	ID theta npair'
    p[0] = {}
    p[0]["id"] = p[1]
    p[0]["theta"] = p[2]
    p[0]["npair"] = p[3]

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
(x <= y - 24)
'''
result = parser.parse(s)
print(result)
