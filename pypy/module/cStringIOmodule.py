"""Bootstrap the builtin cStringIO module.

"""
import sys

from pypy.interpreter.extmodule import ExtModule

_names = sys.builtin_module_names

# We use the second (metaclassish) meaning of type to construct a subclass
#   of ExtModule - can't modify some attributes (like __doc__) after class
#   creation, and wrapping code does not properly look at instance variables.

def CStringIO(space):
    if 'cStringIO' in _names:
        import cStringIO
        _cStringIO = type('cStringIO', (ExtModule,), cStringIO.__dict__)
        return _cStringIO(space)
    else:
        return None
