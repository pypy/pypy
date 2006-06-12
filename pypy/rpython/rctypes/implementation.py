# Base classes describing annotation and rtyping
from pypy.annotation.model import SomeCTypesObject
from pypy.rpython import extregistry
from pypy.rpython.extregistry import ExtRegistryEntry

# rctypes version of ctypes.CFUNCTYPE.
# It's required to work around three limitations of CFUNCTYPE:
#
#   * There is no PY_ version to make callbacks for CPython, which
#     expects the callback to follow the usual conventions (NULL = error).
#
#   * The wrapped callback is not exposed in any special attribute, so
#     if rctypes sees a CFunctionType object it can't find the Python callback
#
#   * I would expect a return type of py_object to mean that if the
#     callback Python function returns a py_object, the C caller sees the
#     PyObject* inside.  Wrong: it sees the py_object wrapper itself.  For
#     consistency -- and also because unwrapping the py_object manually is
#     not allowed annotation-wise -- we change the semantics here under
#     the nose of the annotator.

##_c_callback_functype_cache = {}
##def CALLBACK_FUNCTYPE(restype, *argtypes, **flags):
##    if 'callconv' in flags:
##        callconv = flags.pop('callconv')
##    else:
##        callconv = ctypes.CDLL
##    assert not flags, "unknown keyword arguments %r" % (flags.keys(),)
##    try:
##        return _c_callback_functype_cache[(restype, argtypes)]
##    except KeyError:
##        class CallbackFunctionType(ctypes._CFuncPtr):
##            _argtypes_ = argtypes
##            _restype_ = restype
##            _flags_ = callconv._FuncPtr._flags_

##            def __new__(cls, callback):
##                assert callable(callback)
##                if issubclass(restype, ctypes.py_object):
##                    def func(*args, **kwds):
##                        w_res = callback(*args, **kwds)
##                        assert isinstance(w_res, py_object)
##                        return w_res.value
##                else:
##                    func = callback
##                res = super(CallbackFunctionType, cls).__new__(cls, func)
##                res.callback = callback
##                return res

##        _c_callback_functype_cache[(restype, argtypes)] = CallbackFunctionType
##        return CallbackFunctionType

# ____________________________________________________________

class CTypesEntry(ExtRegistryEntry):
    pass

##    def compute_annotation(self):
##        self.ctype_object_discovered()
##        return super(CTypesEntry, self).compute_annotation()

##    def ctype_object_discovered(self):
##        if self.instance is None:
##            return
##        from pypy.annotation.bookkeeper import getbookkeeper
##        bookkeeper = getbookkeeper()
##        if bookkeeper is None:
##            return
##        # follow all dependent ctypes objects in order to discover
##        # all callback functions
##        memo = {}
##        def recfind(o):
##            if id(o) in memo:
##                return
##            memo[id(o)] = o
##            if isinstance(o, dict):
##                for x in o.itervalues():
##                    recfind(x)
##            elif isinstance(o, (list, tuple)):
##                for x in o:
##                    recfind(x)
##            elif extregistry.is_registered(o):
##                entry = extregistry.lookup(o)
##                if isinstance(entry, CTypesEntry):
##                    entry.object_seen(bookkeeper)
##                    recfind(o._objects)
##                    recfind(o.__dict__)   # for extra keepalives
##        recfind(self.instance)

##    def object_seen(self, bookkeeper):
##        """To be overriden for ctypes objects whose mere presence influences
##        annotation, e.g. callback functions."""

class CTypesCallEntry(CTypesEntry):
    "Annotation and rtyping of calls to ctypes types."

    def compute_result_annotation(self, *args_s, **kwds_s):
        ctype = self.instance    # the ctype is the called object
        return SomeCTypesObject(ctype, SomeCTypesObject.OWNSMEMORY)

class CTypesObjEntry(CTypesEntry):
    "Annotation and rtyping of ctypes instances."

    def compute_annotation(self):
        #self.ctype_object_discovered()
        ctype = self.type
        return SomeCTypesObject(ctype, SomeCTypesObject.OWNSMEMORY)


# Importing for side effect of registering types with extregistry
import pypy.rpython.rctypes.aprimitive
import pypy.rpython.rctypes.apointer
import pypy.rpython.rctypes.aarray
import pypy.rpython.rctypes.afunc
import pypy.rpython.rctypes.achar_p
import pypy.rpython.rctypes.astruct
import pypy.rpython.rctypes.avoid_p
import pypy.rpython.rctypes.astringbuf
import pypy.rpython.rctypes.apyobject
