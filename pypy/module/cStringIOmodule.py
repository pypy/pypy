"""Bootstrap the builtin cStringIO module.

"""
from pypy.interpreter.extmodule import ExtModule

# We use the second (metaclassish) meaning of type to construct a subclass
#   of ExtModule - can't modify some attributes (like __doc__) after class
#   creation, and wrapping code does not properly look at instance variables.

def CStringIO(space):
    try:
        import cStringIO
    except ImportError:
        return None
    _cStringIO = type('cStringIO', (ExtModule,), cStringIO.__dict__)
    return _cStringIO(space)
