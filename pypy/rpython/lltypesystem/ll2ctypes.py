import sys
import ctypes
import ctypes.util
from pypy.rpython.lltypesystem import lltype


_ctypes_cache = {
    lltype.Signed: ctypes.c_long,
    lltype.Char:   ctypes.c_ubyte,
    }

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

        def _getitem(self, index):
            cobj = self.items[index]
            return ctypes2lltype(ITEM, cobj)

        def _setitem(self, index, value):
            cobj = lltype2ctypes(value)
            self.items[index] = cobj

    CArray.__name__ = 'ctypes_%s*%d' % (A, max_n)
    if max_n > 0:
        CArray._normalized_ctype = get_ctypes_type(A)
    return CArray

def get_ctypes_type(T):
    try:
        return _ctypes_cache[T]
    except KeyError:
        if isinstance(T, lltype.Ptr):
            cls = ctypes.POINTER(get_ctypes_type(T.TO))
        elif isinstance(T, lltype.Struct):
            cls = build_ctypes_struct(T)
        elif isinstance(T, lltype.Array):
            cls = build_ctypes_array(T)
        else:
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
        delattr(container, field_name)
        if not isinstance(field_value, lltype._uninitialized):
            setattr(cstruct, field_name, lltype2ctypes(field_value))

def convert_array(container):
    ARRAY = container._TYPE
    cls = get_ctypes_type(ARRAY)
    carray = cls._malloc(container.getlength())
    container._ctypes_storage = carray
    for i in range(container.getlength()):
        item_value = container.items[i]    # fish fish
        container.items[i] = None
        if not isinstance(item_value, lltype._uninitialized):
            carray.items[i] = lltype2ctypes(item_value)

# ____________________________________________________________

def lltype2ctypes(llobj, normalize=True):
    """Convert the lltype object 'llobj' to its ctypes equivalent.
    'normalize' should only be False in tests, where we want to
    inspect the resulting ctypes object manually.
    """
    T = lltype.typeOf(llobj)
    if isinstance(T, lltype.Ptr):
        container = llobj._obj
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

    if T is lltype.Char:
        return ord(llobj)

    return llobj

def ctypes2lltype(T, cobj):
    """Convert the ctypes object 'cobj' to its lltype equivalent.
    'T' is the expected lltype type.
    """
    if T is lltype.Char:
        llobj = chr(cobj)
    else:
        llobj = cobj

    assert lltype.typeOf(llobj) == T
    return llobj

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
    cfunc.restype = get_ctypes_type(FUNCTYPE.RESULT)
    return cfunc

def make_callable_via_ctypes(funcptr):
    try:
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
