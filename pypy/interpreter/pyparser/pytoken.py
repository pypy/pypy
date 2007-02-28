# A replacement for the token module
#
# adds a new map token_values to avoid doing getattr on the module
# from PyPy RPython

N_TOKENS = 0

# This is used to replace None
NULLTOKEN = -1

tok_name = {-1 : 'NULLTOKEN'}
tok_values = {'NULLTOKEN' : -1}

# tok_rpunct = {}

def setup_tokens( parser ):
    # global tok_rpunct
# For compatibility, this produces the same constant values as Python 2.4.
    parser.add_token( 'ENDMARKER' )
    parser.add_token( 'NAME' )
    parser.add_token( 'NUMBER' )
    parser.add_token( 'STRING' )
    parser.add_token( 'NEWLINE' )
    parser.add_token( 'INDENT' )
    parser.add_token( 'DEDENT' )
    parser.add_token( 'LPAR',            "(" )
    parser.add_token( 'RPAR',            ")" )
    parser.add_token( 'LSQB',            "[" )
    parser.add_token( 'RSQB',            "]" )
    parser.add_token( 'COLON',           ":" )
    parser.add_token( 'COMMA',           "," )
    parser.add_token( 'SEMI',            ";" )
    parser.add_token( 'PLUS',            "+" )
    parser.add_token( 'MINUS',           "-" )
    parser.add_token( 'STAR',            "*" )
    parser.add_token( 'SLASH',           "/" )
    parser.add_token( 'VBAR',            "|" )
    parser.add_token( 'AMPER',           "&" )
    parser.add_token( 'LESS',            "<" )
    parser.add_token( 'GREATER',         ">" )
    parser.add_token( 'EQUAL',           "=" )
    parser.add_token( 'DOT',             "." )
    parser.add_token( 'PERCENT',         "%" )
    parser.add_token( 'BACKQUOTE',       "`" )
    parser.add_token( 'LBRACE',          "{" )
    parser.add_token( 'RBRACE',          "}" )
    parser.add_token( 'EQEQUAL',         "==" )
    ne = parser.add_token( 'NOTEQUAL',   "!=" )
    parser.tok_values["<>"] = ne
    parser.add_token( 'LESSEQUAL',       "<=" )
    parser.add_token( 'GREATEREQUAL',    ">=" )
    parser.add_token( 'TILDE',           "~" )
    parser.add_token( 'CIRCUMFLEX',      "^" )
    parser.add_token( 'LEFTSHIFT',       "<<" )
    parser.add_token( 'RIGHTSHIFT',      ">>" )
    parser.add_token( 'DOUBLESTAR',      "**" )
    parser.add_token( 'PLUSEQUAL',       "+=" )
    parser.add_token( 'MINEQUAL',        "-=" )
    parser.add_token( 'STAREQUAL',       "*=" )
    parser.add_token( 'SLASHEQUAL',      "/=" )
    parser.add_token( 'PERCENTEQUAL',    "%=" )
    parser.add_token( 'AMPEREQUAL',      "&=" )
    parser.add_token( 'VBAREQUAL',       "|=" )
    parser.add_token( 'CIRCUMFLEXEQUAL', "^=" )
    parser.add_token( 'LEFTSHIFTEQUAL',  "<<=" )
    parser.add_token( 'RIGHTSHIFTEQUAL', ">>=" )
    parser.add_token( 'DOUBLESTAREQUAL', "**=" )
    parser.add_token( 'DOUBLESLASH',     "//" )
    parser.add_token( 'DOUBLESLASHEQUAL',"//=" )
    parser.add_token( 'AT',              "@" )
    parser.add_token( 'OP' )
    parser.add_token( 'ERRORTOKEN' )

# extra PyPy-specific tokens
    parser.add_token( "COMMENT" )
    parser.add_token( "NL" )

    # tok_rpunct = parser.tok_values.copy()
    # for _name, _value in parser.tokens.items():
    # globals()[_name] = _value
    # setattr(parser, _name, _value)
