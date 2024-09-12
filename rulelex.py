# ------------------------------------------------------------
# constraintlex.py
#
# tokenizer for a simple expression evaluator for
# constraint rules
# ------------------------------------------------------------
import ply.lex as lex

# List of token names.   This is always required
reserved = {
	'COUNTU':'COUNTU',
	'SUM' 	: 'SUM',
	'MAX' 	: 'MAX',
	'MIN' 	: 'MIN',
	'AVG'	: 'AVG',
	'STDEV' : 'STDEV',
	'TIME' 	: 'MOD',
	'TUMBLING': 'TUMBLING',
	'SLIDING': 'SLIDING',
	'IN'	: 'IN',
	'INTERNAL': 'INTERNAL'
}

tokens = [
   'NUMBER',
   'LPAREN',
   'RPAREN',
   'ID',
   'COLON',
   'COMMA',
   'AT',
   'GT',
   'LT',
   'GTE',
   'LTE',
   'EQ',
   'FA',
   'BA',
   'PLUS',
   'MINUS'
] + list(reserved.values())

# Regular expression rules for simple tokens
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_COLON	  = r':'
t_COMMA	  = r','
t_AT	  = r'@'
t_GT	  = r'>'
t_LT	  = r'<'
t_GTE	  = r'>='
t_LTE	  = r'<='
t_EQ	  = r'='
t_FA	  = r'->'
t_BA	  = r'<-'
t_PLUS	  = r'\+'
t_MINUS	  = r'-'
# A regular expression rule with some action code
def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)    
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value,'ID')    # Check for reserved words
    return t

# Define a rule so we can track line numbers
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# A string containing ignored characters (spaces and tabs)
t_ignore  = ' \t'

# Error handling rule
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

t_ignore_COMMENT = r'\#.*'

# Build the lexer
lexer = lex.lex()

# Test it out
data = '''
# Calculation Rule
S1: INTERNAL calcsum(a1, a2, ax=SUM(x)) <-
eva(a1, a2, x)@z IN SLIDING (s, 5), 
# Business Rule
R1: RentBike(Bid, Cid)@x, ReturnBike(Bid, Cid)@y -> 
x <= y - 24 
'''

# Give the lexer some input
lexer.input(data)

# Tokenize
while True:
    tok = lexer.token()
    if not tok: 
        break      # No more input
    print(tok)
