"""Bootstrap the builtin time module.

"""
from pypy.interpreter.extmodule import ExtModule

# We use the second (metaclassish) meaning of type to construct a subclass
#   of ExtModule - can't modify some attributes (like __doc__) after class
#   creation, and wrapping code does not properly look at instance variables.

def Time(space):
    try:
        import time
    except ImportError:
        return None
    _time = type('time', (ExtModule,), time.__dict__)
    return _time(space)
