# A replacement for the token module
#
# adds a new map token_values to avoid doing getattr on the module
# from PyPy RPython

import token

N_TOKENS = token.N_TOKENS

tok_name = {}
tok_values = {}

def add_token(name, value=None):
    global N_TOKENS
    if value is None:
        value = N_TOKENS
        N_TOKENS += 1
    _g = globals()
    _g[name] = value
    tok_name[value] = name
    tok_values[name] = value

# This is used to replace None
add_token( 'NULLTOKEN', -1 )

for value, name in token.tok_name.items():
    add_token( name, value )

# Make sure '@' is in the token list
if "AT" not in tok_values:
    add_token( "AT" )

add_token( "COMMENT" )
add_token( "NL" )

# a reverse mapping from internal tokens def to more pythonic tokens
tok_punct = {
    "&" : AMPER,
    "&=" : AMPEREQUAL,
    "`" : BACKQUOTE,
    "^" : CIRCUMFLEX,
    "^=" : CIRCUMFLEXEQUAL,
    ":" : COLON,
    "," : COMMA,
    "." : DOT,
    "//" : DOUBLESLASH,
    "//=" : DOUBLESLASHEQUAL,
    "**" : DOUBLESTAR,
    "**=" : DOUBLESTAREQUAL,
    "==" : EQEQUAL,
    "=" : EQUAL,
    ">" : GREATER,
    ">=" : GREATEREQUAL,
    "{" : LBRACE,
    "}" : RBRACE,
    "<<" : LEFTSHIFT,
    "<<=" : LEFTSHIFTEQUAL,
    "<" : LESS,
    "<=" : LESSEQUAL,
    "(" : LPAR,
    "[" : LSQB,
    "-=" : MINEQUAL,
    "-" : MINUS,
    "!=" : NOTEQUAL,
    "<>" : NOTEQUAL,
    "%" : PERCENT,
    "%=" : PERCENTEQUAL,
    "+" : PLUS,
    "+=" : PLUSEQUAL,
    ")" : RBRACE,
    ">>" : RIGHTSHIFT,
    ">>=" : RIGHTSHIFTEQUAL,
    ")" : RPAR,
    "]" : RSQB,
    ";" : SEMI,
    "/" : SLASH,
    "/=" : SLASHEQUAL,
    "*" : STAR,
    "*=" : STAREQUAL,
    "~" : TILDE,
    "|" : VBAR,
    "|=" : VBAREQUAL,
    "@": AT,
    }
tok_rpunct = {}
for string, value in tok_punct.items():
    tok_rpunct[value] = string

