"""Bootstrap the builtin _random module.

"""
from pypy.interpreter.extmodule import ExtModule

# We use the second (metaclassish) meaning of type to construct a subclass
#   of ExtModule - can't modify some attributes (like __doc__) after class
#   creation, and wrapping code does not properly look at instance variables.

def RandomHelper(space):
    try:
        import _random
    except ImportError:
        return None
    _randomhelper = type('_random', (ExtModule,), _random.__dict__)
    return _randomhelper(space)
