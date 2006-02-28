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


# Export the values from our custom symbol module.
# Skip negative values (the corresponding symbols are not visible in
# pure Python).
from pypy.interpreter.pyparser.pythonparse import PYTHON_PARSER

sym_name = {}
for val, name in PYTHON_PARSER.symbols.sym_name.items():
    if val >= 0:
        Module.interpleveldefs[name] = 'space.wrap(%d)' % val
        sym_name[val] = name
Module.interpleveldefs['sym_name'] = 'space.wrap(%r)' % (sym_name,)
