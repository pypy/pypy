import sys
import ctypes
import ctypes.util
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rlib.objectmodel import Symbolic
from pypy.tool.uid import fixid
from pypy.rlib.rarithmetic import r_uint


def uaddressof(obj):
    return fixid(ctypes.addressof(obj))


_ctypes_cache = {}

def _setup_ctypes_cache():
    from pypy.rpython.lltypesystem import rffi
    _ctypes_cache.update({
        lltype.Signed:   ctypes.c_long,
        lltype.Unsigned: ctypes.c_ulong,
        lltype.Char:     ctypes.c_ubyte,
        rffi.DOUBLE:     ctypes.c_double,
        rffi.SIGNEDCHAR: ctypes.c_byte,
        rffi.UCHAR:      ctypes.c_ubyte,
        rffi.SHORT:      ctypes.c_short,
        rffi.USHORT:     ctypes.c_ushort,
        rffi.INT:        ctypes.c_int,
        rffi.UINT:       ctypes.c_uint,
        rffi.LONG:       ctypes.c_long,
        rffi.ULONG:      ctypes.c_ulong,
        rffi.LONGLONG:   ctypes.c_longlong,
        rffi.ULONGLONG:  ctypes.c_ulonglong,
        rffi.SIZE_T:     ctypes.c_size_t,
        })

def build_ctypes_struct(S, max_n=None):
    fields = []
    for fieldname in S._names:
        FIELDTYPE = S._flds[fieldname]
        if max_n is not None and fieldname == S._arrayfld:
            cls = build_ctypes_array(FIELDTYPE, max_n)
        else:
            cls = get_ctypes_type(FIELDTYPE)
        fields.append((fieldname, cls))

    class CStruct(ctypes.Structure):
        _fields_ = fields

        def _malloc(cls, n=None):
            if S._arrayfld is None:
                if n is not None:
                    raise TypeError("%r is not variable-sized" % (S,))
                storage = cls()
                return storage
            else:
                if n is None:
                    raise TypeError("%r is variable-sized" % (S,))
                biggercls = build_ctypes_struct(S, n)
                bigstruct = biggercls()
                array = getattr(bigstruct, S._arrayfld)
                if hasattr(array, 'length'):
                    array.length = n
                return bigstruct
        _malloc = classmethod(_malloc)

        def _getattr(self, field_name):
            T = getattr(S, field_name)
            cobj = getattr(self, field_name)
            return ctypes2lltype(T, cobj)

        def _setattr(self, field_name, value):
            cobj = lltype2ctypes(value)
            setattr(self, field_name, cobj)

        def _eq(self, other):
            return ctypes.addressof(self) == ctypes.addressof(other)

    CStruct.__name__ = 'ctypes_%s' % (S,)
    if max_n is not None:
        CStruct._normalized_ctype = get_ctypes_type(S)
    return CStruct

def build_ctypes_array(A, max_n=0):
    assert max_n >= 0
    ITEM = A.OF
    ctypes_item = get_ctypes_type(ITEM)

    class CArray(ctypes.Structure):
        if not A._hints.get('nolength'):
            _fields_ = [('length', ctypes.c_int),
                        ('items',  max_n * ctypes_item)]
        else:
            _fields_ = [('items',  max_n * ctypes_item)]

        def _malloc(cls, n=None):
            if not isinstance(n, int):
                raise TypeError, "array length must be an int"
            biggercls = build_ctypes_array(A, n)
            bigarray = biggercls()
            if hasattr(bigarray, 'length'):
                bigarray.length = n
            return bigarray
        _malloc = classmethod(_malloc)

        def _indexable(self, index):
            PtrType = ctypes.POINTER((index+1) * ctypes_item)
            p = ctypes.cast(ctypes.pointer(self.items), PtrType)
            return p.contents

        def _getitem(self, index, boundscheck=True):
            if boundscheck:
                items = self.items
            else:
                items = self._indexable(index)
            cobj = items[index]
            return ctypes2lltype(ITEM, cobj)

        def _setitem(self, index, value, boundscheck=True):
            if boundscheck:
                items = self.items
            else:
                items = self._indexable(index)
            cobj = lltype2ctypes(value)
            items[index] = cobj

        def _eq(self, other):
            return ctypes.addressof(self) == ctypes.addressof(other)

    CArray.__name__ = 'ctypes_%s*%d' % (A, max_n)
    if max_n > 0:
        CArray._normalized_ctype = get_ctypes_type(A)
    return CArray

def get_ctypes_type(T):
    try:
        return _ctypes_cache[T]
    except KeyError:
        if isinstance(T, lltype.Ptr):
            if isinstance(T.TO, lltype.FuncType):
                argtypes = [get_ctypes_type(ARG) for ARG in T.TO.ARGS]
                if T.TO.RESULT is lltype.Void:
                    restype = None
                else:
                    restype = get_ctypes_type(T.TO.RESULT)
                cls = ctypes.CFUNCTYPE(restype, *argtypes)
            else:
                cls = ctypes.POINTER(get_ctypes_type(T.TO))
        elif isinstance(T, lltype.Struct):
            cls = build_ctypes_struct(T)
        elif isinstance(T, lltype.Array):
            cls = build_ctypes_array(T)
        else:
            _setup_ctypes_cache()
            if T in _ctypes_cache:
                return _ctypes_cache[T]
            raise NotImplementedError(T)
        _ctypes_cache[T] = cls
        return cls


def convert_struct(container):
    STRUCT = container._TYPE
    cls = get_ctypes_type(STRUCT)
    cstruct = cls._malloc()
    container._ctypes_storage = cstruct
    for field_name in STRUCT._names:
        field_value = getattr(container, field_name)
        setattr(cstruct, field_name, lltype2ctypes(field_value))
    remove_regular_struct_content(container)

def remove_regular_struct_content(container):
    STRUCT = container._TYPE
    for field_name in STRUCT._names:
        delattr(container, field_name)

def convert_array(container):
    ARRAY = container._TYPE
    cls = get_ctypes_type(ARRAY)
    carray = cls._malloc(container.getlength())
    container._ctypes_storage = carray
    for i in range(container.getlength()):
        item_value = container.items[i]    # fish fish
        carray.items[i] = lltype2ctypes(item_value)
    remove_regular_array_content(container)

def remove_regular_array_content(container):
    for i in range(container.getlength()):
        container.items[i] = None

class _array_of_unknown_length(lltype._parentable):
    _kind = "array"

    __slots__ = ()

    def __repr__(self):
        return '<C array at 0x%x>' % (uaddressof(self._ctypes_storage),)

    def getbounds(self):
        # we have no clue, so we allow whatever index
        return 0, sys.maxint

    def getitem(self, index, uninitialized_ok=False):
        return self._ctypes_storage._getitem(index, boundscheck=False)

    def setitem(self, index, value):
        self._ctypes_storage._setitem(index, value, boundscheck=False)

# ____________________________________________________________

def lltype2ctypes(llobj, normalize=True):
    """Convert the lltype object 'llobj' to its ctypes equivalent.
    'normalize' should only be False in tests, where we want to
    inspect the resulting ctypes object manually.
    """
    if isinstance(llobj, lltype._uninitialized):
        return uninitialized2ctypes(llobj.TYPE)

    T = lltype.typeOf(llobj)
    if isinstance(T, lltype.Ptr):
        container = llobj._obj
        if isinstance(T.TO, lltype.FuncType):
            if not hasattr(container, '_callable'):
                raise NotImplementedError("ctypes wrapper for ll function "
                                          "without a _callable")
            else:
                ctypes_func_type = get_ctypes_type(T)
                def callback(*cargs):
                    assert len(cargs) == len(T.TO.ARGS)
                    llargs = [ctypes2lltype(ARG, cargs)
                              for ARG, cargs in zip(T.TO.ARGS, cargs)]
                    llres = container._callable(*llargs)
                    assert lltype.typeOf(llres) == T.TO.RESULT
                    if T.TO.RESULT is lltype.Void:
                        return None
                    else:
                        return lltype2ctypes(llres)
                return ctypes_func_type(callback)

        if container._ctypes_storage is None:
            if isinstance(T.TO, lltype.Struct):
                convert_struct(container)
            elif isinstance(T.TO, lltype.Array):
                convert_array(container)
            else:
                raise NotImplementedError(T)
        storage = container._ctypes_storage
        p = ctypes.pointer(storage)
        if normalize and hasattr(storage, '_normalized_ctype'):
            p = ctypes.cast(p, ctypes.POINTER(storage._normalized_ctype))
        return p

    if isinstance(llobj, Symbolic):
        if isinstance(llobj, llmemory.ItemOffset):
            llobj = ctypes.sizeof(get_ctypes_type(llobj.TYPE)) * llobj.repeat
        else:
            raise NotImplementedError(llobj)  # don't know about symbolic value

    if T is lltype.Char:
        return ord(llobj)

    return llobj

def ctypes2lltype(T, cobj):
    """Convert the ctypes object 'cobj' to its lltype equivalent.
    'T' is the expected lltype type.
    """
    if isinstance(T, lltype.Ptr):
        if isinstance(T.TO, lltype.Struct):
            # XXX var-sized structs
            container = lltype._struct(T.TO)
            container._ctypes_storage = cobj.contents
            remove_regular_struct_content(container)
        elif isinstance(T.TO, lltype.Array):
            if T.TO._hints.get('nolength', False):
                container = _array_of_unknown_length(T.TO)
                container._ctypes_storage = cobj.contents
            else:
                raise NotImplementedError("array with an explicit length")
        elif isinstance(T.TO, lltype.FuncType):
            funcptr = lltype.functionptr(T.TO, getattr(cobj, '__name__', '?'))
            make_callable_via_ctypes(funcptr, cfunc=cobj)
            return funcptr
        else:
            raise NotImplementedError(T)
        llobj = lltype._ptr(T, container, solid=True)
    elif T is lltype.Char:
        llobj = chr(cobj)
    elif T is lltype.Unsigned:
        llobj = r_uint(cobj)
    else:
        llobj = cobj

    assert lltype.typeOf(llobj) == T
    return llobj

def uninitialized2ctypes(T):
    "For debugging, create a ctypes object filled with 0xDD."
    ctype = get_ctypes_type(T)
    cobj = ctype()
    size = ctypes.sizeof(cobj)
    p = ctypes.cast(ctypes.pointer(cobj),
                    ctypes.POINTER(ctypes.c_ubyte * size))
    for i in range(size):
        p.contents[i] = 0xDD
    if isinstance(T, lltype.Primitive):
        return cobj.value
    else:
        return cobj

# __________ the standard C library __________

if sys.platform == 'win32':
    standard_c_lib = ctypes.cdll.LoadLibrary('msvcrt.dll')
else:
    standard_c_lib = ctypes.cdll.LoadLibrary(ctypes.util.find_library('c'))

# ____________________________________________

def get_ctypes_callable(funcptr):
    if getattr(funcptr._obj, 'source', None) is not None:
        # give up - for tests with an inlined bit of C code
        raise NotImplementedError("cannot call a C function defined in "
                                  "a custom C source snippet")
    FUNCTYPE = lltype.typeOf(funcptr).TO
    funcname = funcptr._obj._name
    libraries = getattr(funcptr._obj, 'libraries', None)
    if not libraries:
        cfunc = getattr(standard_c_lib, funcname, None)
    else:
        cfunc = None
        for libname in libraries:
            libpath = ctypes.util.find_library(libname)
            if libpath:
                clib = ctypes.cdll.LoadLibrary(libpath)
                cfunc = getattr(clib, funcname, None)
                if cfunc is not None:
                    break

    if cfunc is None:
        # function name not found in any of the libraries
        if not libraries:
            place = 'the standard C library'
        elif len(libraries) == 1:
            place = 'library %r' % (libraries[0],)
        else:
            place = 'any of the libraries %r' % (libraries,)
        raise NotImplementedError("function %r not found in %s" % (
            funcname, place))

    # get_ctypes_type() can raise NotImplementedError too
    cfunc.argtypes = [get_ctypes_type(T) for T in FUNCTYPE.ARGS]
    if FUNCTYPE.RESULT is lltype.Void:
        cfunc.restype = None
    else:
        cfunc.restype = get_ctypes_type(FUNCTYPE.RESULT)
    return cfunc

def make_callable_via_ctypes(funcptr, cfunc=None):
    try:
        if cfunc is None:
            cfunc = get_ctypes_callable(funcptr)
    except NotImplementedError, e:
        def invoke_via_ctypes(*argvalues):
            raise NotImplementedError, e
    else:
        RESULT = lltype.typeOf(funcptr).TO.RESULT
        def invoke_via_ctypes(*argvalues):
            cargs = [lltype2ctypes(value) for value in argvalues]
            cres = cfunc(*cargs)
            return ctypes2lltype(RESULT, cres)
    funcptr._obj._callable = invoke_via_ctypes

def force_cast(PTRTYPE, ptr):
    """Cast a pointer to another pointer with no typechecking."""
    CPtrType = get_ctypes_type(PTRTYPE)
    cptr = lltype2ctypes(ptr)
    cptr = ctypes.cast(cptr, CPtrType)
    return ctypes2lltype(PTRTYPE, cptr)
