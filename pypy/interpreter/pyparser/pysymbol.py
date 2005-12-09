# replacement for the CPython symbol module
try:
    from pypy.interpreter.pyparser import symbol
except ImportError:
    # for standalone testing
    import symbol

# try to avoid numeric values conflict with tokens
# it's important for CPython, but I'm not so sure it's still
# important here

class SymbolMapper(object):
    def __init__(self, sym_name=None ):
        _anoncount = self._anoncount = -10
        _count = self._count = 0
        self.sym_name = {}
        self.sym_values = {}
        if sym_name is not None:
            for _value, _name in sym_name.items():
                if _value<_anoncount:
                    _anoncount = _value
                if _value>_count:
                    _count = _value
                self.sym_values[_name] = _value
                self.sym_name[_value] = _name
            self._anoncount = _anoncount
            self._count = _count

    def add_symbol( self, sym ):
        assert type(sym)==str
        if not sym in self.sym_values:
            self._count += 1
            val = self._count
            self.sym_values[sym] = val
            self.sym_name[val] = sym
            return val
        return self.sym_values[ sym ]

    def add_anon_symbol( self, sym ):
        assert type(sym)==str
        if not sym in self.sym_values:
            self._anoncount -= 1
            val = self._anoncount
            self.sym_values[sym] = val
            self.sym_name[val] = sym
            return val
        return self.sym_values[ sym ]

    def __getitem__(self, sym ):
        """NOT RPYTHON"""
        assert type(sym)==str
        return self.sym_values[ sym ]
    

_cpython_symbols = SymbolMapper( symbol.sym_name )


# prepopulate symbol table from symbols used by CPython
for _value, _name in _cpython_symbols.sym_name.items():
    globals()[_name] = _value

    

def update_symbols( parser ):
    """Update the symbol module according to rules
    in PythonParser instance : parser"""
    for rule in parser.rules:
        _cpython_symbols.add_symbol( rule )

# There is no symbol in this module until the grammar is loaded
# once loaded the grammar parser will fill the mappings with the
# grammar symbols
