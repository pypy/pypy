"""Bootstrap the builtin math module.

"""
from pypy.interpreter.extmodule import ExtModule

# We use the second (metaclassish) meaning of type to construct a subclass
#   of ExtModule - can't modify some attributes (like __doc__) after class
#   creation, and wrapping code does not properly look at instance variables.

def Math(space):
    try:
        import math
    except ImportError:
        return None
    _math = type('math', (ExtModule,), math.__dict__)
    return _math(space)
