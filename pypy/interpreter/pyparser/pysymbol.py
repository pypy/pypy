# replacement for the CPython symbol module
from pytoken import N_TOKENS

# try to avoid numeric values conflict with tokens
# it's important for CPython, but I'm not so sure it's still
# important here
SYMBOL_START = N_TOKENS+30
del N_TOKENS

_count = SYMBOL_START
_anoncount = -10

sym_name = {}
sym_values = {}

def add_symbol( sym ):
    global _count
    assert type(sym)==str
    if not sym_values.has_key( sym ):
        val = _count
        sym_values[sym] = val
        sym_name[val] = sym
        globals()[sym] = val
        _count += 1
        return val
    return sym_values[ sym ]

def add_anon_symbol( sym ):
    global _anoncount
    assert type(sym)==str
    if not sym_values.has_key( sym ):
        val = _anoncount
        sym_values[sym] = val
        sym_name[val] = sym
        _anoncount -= 1
        return val
    return sym_values[ sym ]
    

def update_symbols( parser ):
    """Update the symbol module according to rules
    in PythonParser instance : parser"""
    for rule in parser.rules:
        add_symbol( rule )

# There is no symbol in this module until the grammar is loaded
# once loaded the grammar parser will fill the mappings with the
# grammar symbols
