"""Bootstrap the builtin math module.

"""
import sys

from pypy.interpreter.extmodule import ExtModule

_names = sys.builtin_module_names

# We use the second (metaclassish) meaning of type to construct a subclass
#   of ExtModule - can't modify some attributes (like __doc__) after class
#   creation, and wrapping code does not properly look at instance variables.

def Math(space):
    if 'math' in _names:
        import math
        _math = type('math', (ExtModule,), math.__dict__)
        return _math(space)
    else:
        return None
