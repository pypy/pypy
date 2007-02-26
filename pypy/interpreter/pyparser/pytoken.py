# A replacement for the token module
#
# adds a new map token_values to avoid doing getattr on the module
# from PyPy RPython

N_TOKENS = 0

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

# For compatibility, this produces the same constant values as Python 2.4.
add_token( 'ENDMARKER' )
add_token( 'NAME' )
add_token( 'NUMBER' )
add_token( 'STRING' )
add_token( 'NEWLINE' )
add_token( 'INDENT' )
add_token( 'DEDENT' )
add_token( 'LPAR' )
add_token( 'RPAR' )
add_token( 'LSQB' )
add_token( 'RSQB' )
add_token( 'COLON' )
add_token( 'COMMA' )
add_token( 'SEMI' )
add_token( 'PLUS' )
add_token( 'MINUS' )
add_token( 'STAR' )
add_token( 'SLASH' )
add_token( 'VBAR' )
add_token( 'AMPER' )
add_token( 'LESS' )
add_token( 'GREATER' )
add_token( 'EQUAL' )
add_token( 'DOT' )
add_token( 'PERCENT' )
add_token( 'BACKQUOTE' )
add_token( 'LBRACE' )
add_token( 'RBRACE' )
add_token( 'EQEQUAL' )
add_token( 'NOTEQUAL' )
add_token( 'LESSEQUAL' )
add_token( 'GREATEREQUAL' )
add_token( 'TILDE' )
add_token( 'CIRCUMFLEX' )
add_token( 'LEFTSHIFT' )
add_token( 'RIGHTSHIFT' )
add_token( 'DOUBLESTAR' )
add_token( 'PLUSEQUAL' )
add_token( 'MINEQUAL' )
add_token( 'STAREQUAL' )
add_token( 'SLASHEQUAL' )
add_token( 'PERCENTEQUAL' )
add_token( 'AMPEREQUAL' )
add_token( 'VBAREQUAL' )
add_token( 'CIRCUMFLEXEQUAL' )
add_token( 'LEFTSHIFTEQUAL' )
add_token( 'RIGHTSHIFTEQUAL' )
add_token( 'DOUBLESTAREQUAL' )
add_token( 'DOUBLESLASH' )
add_token( 'DOUBLESLASHEQUAL' )
add_token( 'AT' )
add_token( 'OP' )
add_token( 'ERRORTOKEN' )

# extra PyPy-specific tokens
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

