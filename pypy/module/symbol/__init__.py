"""Dynamic replacement for the stdlib 'symbol' module.

This module exports the symbol values computed by the grammar parser
at run-time.
"""

from pypy.interpreter.mixedmodule import MixedModule

# Forward imports so they run at startup time
import pypy.interpreter.pyparser.pythonlexer
import pypy.interpreter.pyparser.pythonparse


class Module(MixedModule):
    """Non-terminal symbols of Python grammar."""
    appleveldefs = {}
    interpleveldefs = {}     # see below

    def __init__(self, space, w_name):
        MixedModule.__init__(self, space, w_name)
        _init_symbols(space.config.objspace.pyversion)


# Export the values from our custom symbol module.
# Skip negative values (the corresponding symbols are not visible in
# pure Python).
sym_name = {}

def _init_symbols(grammar_version):
    global sym_name

    sym_name = {}
    from pypy.interpreter.pyparser.pythonparse import make_pyparser
    parser = make_pyparser(grammar_version)

    for name, val in parser.symbols.items():
        if val >= 0:
            Module.interpleveldefs[name] = 'space.wrap(%d)' % val
            sym_name[val] = name
    Module.interpleveldefs['sym_name'] = 'space.wrap(%r)' % (sym_name,)

# This is very evil
_init_symbols('2.4')
