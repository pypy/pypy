"""Bootstrap the builtin modules which make up sys:
posix, nt, os2, mac, ce, etc.

"""
import sys
import os

from pypy.interpreter.extmodule import ExtModule

_names = sys.builtin_module_names

# We use the second (metaclassish) meaning of type to construct a subclass
#   of ExtModule - can't modify some attributes (like __doc__) after class
#   creation, and wrapping code does not properly look at instance variables.
def Posix(space):
    if 'posix' in _names:
        import posix
        _posix = type('posix', (ExtModule,), posix.__dict__)
        return _posix(space)
    else:
        return None

def Nt(space):
    if 'nt' in _names:
        import nt
        _nt = type('nt', (ExtModule,), nt.__dict__)
        return _nt(space)
    else:
        return None

def Os2(space):
    if 'os2' in _names:
        import os2
        _os2 = type('os2', (ExtModule,), os2.__dict__)
        return _os2(space)
    else:
        return None

def Mac(space):
    if 'mac' in _names:
        import mac
        _mac = type('mac', (ExtModule,), mac.__dict__)
        return _mac(space)
    else:
        return None

def Ce(space):
    if 'ce' in _names:
        import ce
        _ce = type('ce', (ExtModule,), ce.__dict__)
        return _ce(space)
    else:
        return None

def Riscos(space):
    if 'riscos' in _names:
        import riscos
        _riscos = type('riscos', (ExtModule,), riscos.__dict__)
        return _riscos(space)
    else:
        return None
