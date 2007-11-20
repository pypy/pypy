
import _ffi
import sys

DEFAULT_MODE = None # XXX, mode support in _ffi

class ArgumentError(Exception):
    pass

class _CFuncPtr(object):
    def __init__(self, (name, lib)):
        self.name = name
        self.lib = lib
        self._update_handle()

    def __call__(self, *args):
        # XXX right now always update handle in order to keep changing
        #     argtypes and restype
        self._update_handle()
        try:
            return self._handle(*args)
        except TypeError, e:
            raise ArgumentError("Wrong argument", e.__class__)

    def _update_handle(self):
        llargs = [i._type_ for i in self.argtypes]
        # XXX first approximation
        self._handle = self.lib._handle.ptr(self.name, llargs,
                                           self.restype._type_)

from ctypes._basics import *
from ctypes._pointers import POINTER

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
        restype = c_int # default, can be overridden in instances
        argtypes = []

    def __init__(self, name, mode=DEFAULT_MODE, handle=None):
        self._name = name
        if handle is None:
            self._handle = _ffi.CDLL(self._name)
        else:
            self._handle = handle

    def __repr__(self):
        return "<%s '%s', handle>" % \
               (self.__class__.__name__, self._name)

    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError, name
        func = self.__getitem__(name)
        setattr(self, name, func)
        return func

    def __getitem__(self, name_or_ordinal):
        func = self._FuncPtr((name_or_ordinal, self))
        if not isinstance(name_or_ordinal, (int, long)):
            func.__name__ = name_or_ordinal
        return func


class LibraryLoader(object):
    def __init__(self, dlltype):
        self._dlltype = dlltype

    def __getattr__(self, name):
        if name[0] == '_':
            raise AttributeError(name)
        dll = self._dlltype(name)
        setattr(self, name, dll)
        return dll

    def __getitem__(self, name):
        return getattr(self, name)

    def LoadLibrary(self, name):
        return self._dlltype(name)

cdll = LibraryLoader(CDLL)

