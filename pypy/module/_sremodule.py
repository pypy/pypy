"""Bootstrap the builtin _sre module.

"""
import sys

from pypy.interpreter.extmodule import ExtModule

_names = sys.builtin_module_names

# We use the second (metaclassish) meaning of type to construct a subclass
#   of ExtModule - can't modify some attributes (like __doc__) after class
#   creation, and wrapping code does not properly look at instance variables.

def SreHelper(space):
    import _sre
    _srehelper = type('_sre', (ExtModule,), _sre.__dict__)
    return _srehelper(space)
