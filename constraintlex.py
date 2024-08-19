# ------------------------------------------------------------
# calclex.py
#
# tokenizer for a simple expression evaluator for
# numbers and +,-,*,/
# ------------------------------------------------------------
import ply.lex as lex

# List of token names.   This is always required
reserved = {
	'IF' 	:'IF',
	'THEN' 	: 'THEN',
	'MAX' 	: 'MAX',
	'MIN' 	: 'MIN',
	'EALIER': 'EARLIER',
	'LATER' : 'LATER',
	'TIME' 	: 'TIME',
	'OVER' 	: 'OVER',
	'COUNT' : 'COUNT',
	'UNDER' : 'UNDER',
	'CASE' 	: 'CASE',
	'DELETE': 'DELETE'
}

tokens = [
   'NUMBER',
   'LPAREN',
   'RPAREN',
   'ID',
   'COLON',
   'COMMA'
] + list(reserved.values())

# Regular expression rules for simple tokens
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_COLON	  = r':'
t_COMMA	  = r','
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
IF r1:RentBike(cid:x,bid:y) #This is a comment
THEN LATER 1 r2:ReturnBike(cid:x,bid:y) #This is a comment
CASE TIME OVER delete r1
CASE COUNT UNDER delete r2
'''

# Give the lexer some input
lexer.input(data)

# Tokenize
while True:
    tok = lexer.token()
    if not tok: 
        break      # No more input
    print(tok)
