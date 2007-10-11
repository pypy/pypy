
""" App-level part of ctypes module
"""

from _ctypes import dlopen, RTLD_LOCAL, RTLD_GLOBAL
from _ctypes import CFuncPtr as _CFuncPtr
from _ctypes import _SimpleCData

# XXX check size, etc
class c_int(_SimpleCData):
    _type_ = 'i'

DEFAULT_MODE = RTLD_LOCAL

class CDLL(object):
    """An instance of this class represents a loaded dll/shared
    library, exporting functions using the standard C calling
    convention (named 'cdecl' on Windows).

    The exported functions can be accessed as attributes, or by
    indexing with the function name.  Examples:

    <obj>.qsort -> callable object
    <obj>['qsort'] -> callable object

    Calling the functions releases the Python GIL during the call and
    reaquires it afterwards.
    """
    class _FuncPtr(_CFuncPtr):
        #_flags_ = _FUNCFLAG_CDECL
        _restype_ = c_int # default, can be overridden in instances
    
    def __init__(self, name, mode=DEFAULT_MODE, handle=None):
        self._name = name
        if handle is None:
            self._handle = dlopen(name, mode)
        else:
            self._handle = handle

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self._name)

    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError, name
        func = self.__getitem__(name)
        setattr(self, name, func)
        return func

    def __getitem__(self, name_or_ordinal):
        # right now only name
        assert isinstance(name_or_ordinal, (str, unicode))
        func = self._FuncPtr((name_or_ordinal, self))
        if not isinstance(name_or_ordinal, (int, long)):
            func.__name__ = name_or_ordinal
        return func
