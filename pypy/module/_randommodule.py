"""Bootstrap the builtin _random module.

"""
import sys

from pypy.interpreter.extmodule import ExtModule

_names = sys.builtin_module_names

# We use the second (metaclassish) meaning of type to construct a subclass
#   of ExtModule - can't modify some attributes (like __doc__) after class
#   creation, and wrapping code does not properly look at instance variables.

def RandomHelper(space):
    if '_random' in _names:
        import _random
        _randomhelper = type('_random', (ExtModule,), _random.__dict__)
        return _randomhelper(space)
    else:
        return None
