"""Bootstrap the builtin itertools module.

"""
from pypy.interpreter.extmodule import ExtModule

# We use the second (metaclassish) meaning of type to construct a subclass
#   of ExtModule - can't modify some attributes (like __doc__) after class
#   creation, and wrapping code does not properly look at instance variables.

def Itertools(space):
    try:
        import itertools
    except ImportError:
        return None
    _itertools = type('itertools', (ExtModule,), itertools.__dict__)
    return _itertools(space)
