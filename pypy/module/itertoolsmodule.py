"""Bootstrap the builtin itertools module.

"""
import sys

from pypy.interpreter.extmodule import ExtModule

_names = sys.builtin_module_names

# We use the second (metaclassish) meaning of type to construct a subclass
#   of ExtModule - can't modify some attributes (like __doc__) after class
#   creation, and wrapping code does not properly look at instance variables.

def Itertools(space):
    if 'itertools' in _names:
        import itertools
        _itertools = type('itertools', (ExtModule,), itertools.__dict__)
        return _itertools(space)
    else:
        return None
