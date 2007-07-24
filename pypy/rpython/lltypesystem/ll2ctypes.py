import sys
import ctypes
import ctypes.util
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.extfunc import ExtRegistryEntry
from pypy.rlib.objectmodel import Symbolic
from pypy.tool.uid import fixid
from pypy.rlib.rarithmetic import r_uint
from pypy.annotation import model as annmodel
from pypy.rpython.rbuiltin import gen_cast


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
    add_storage(container, _struct_mixin, cstruct)
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
    add_storage(container, _array_mixin, carray)
    for i in range(container.getlength()):
        item_value = container.items[i]    # fish fish
        carray.items[i] = lltype2ctypes(item_value)
    remove_regular_array_content(container)

def remove_regular_array_content(container):
    for i in range(container.getlength()):
        container.items[i] = None

# ____________________________________________________________
# Ctypes-aware subclasses of the _parentable classes

def get_common_subclass(cls1, cls2, cache={}):
    """Return a unique subclass with (cls1, cls2) as bases."""
    try:
        return cache[cls1, cls2]
    except KeyError:
        subcls = type('_ctypes_%s' % (cls1.__name__,),
                      (cls1, cls2),
                      {'__slots__': ()})
        assert '__dict__' not in dir(subcls)   # use __slots__ everywhere
        cache[cls1, cls2] = subcls
        return subcls

def add_storage(instance, mixin_cls, ctypes_storage):
    """Put ctypes_storage on the instance, changing its __class__ so that it
    sees the methods of the given mixin class."""
    assert not isinstance(instance, _parentable_mixin)  # not yet
    subcls = get_common_subclass(mixin_cls, instance.__class__)
    instance.__class__ = subcls
    instance._storage = ctypes_storage

class _parentable_mixin(object):
    """Mixin added to _parentable containers when they become ctypes-based.
    (This is done by changing the __class__ of the instance to reference
    a subclass of both its original class and of this mixin class.)
    """
    __slots__ = ()

    def __eq__(self, other):
        if not isinstance(other, lltype._parentable):
            return False
        if self._storage is None or other._storage is None:
            raise RuntimeError("pointer comparison with a freed structure")
        if other._storage is True:
            return False    # the other container is not ctypes-based
        # both containers are ctypes-based, compare by address
        return (ctypes.addressof(self._storage) ==
                ctypes.addressof(other._storage))

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        if self._storage is None:
            return '<freed C object %s>' % (self._TYPE,)
        else:
            return '<C object %s at 0x%x>' % (self._TYPE,
                                              uaddressof(self._storage),)

    def __str__(self):
        return repr(self)

class _struct_mixin(_parentable_mixin):
    """Mixin added to _struct containers when they become ctypes-based."""
    __slots__ = ()

    def __getattr__(self, field_name):
        T = getattr(self._TYPE, field_name)
        cobj = getattr(self._storage, field_name)
        return ctypes2lltype(T, cobj)

    def __setattr__(self, field_name, value):
        if field_name.startswith('_'):
            object.__setattr__(self, field_name, value)  # '_xxx' attributes
        else:
            cobj = lltype2ctypes(value)
            setattr(self._storage, field_name, cobj)

class _array_mixin(_parentable_mixin):
    """Mixin added to _array containers when they become ctypes-based."""
    __slots__ = ()

    def getitem(self, index, uninitialized_ok=False):
        return self._storage._getitem(index)

    def setitem(self, index, value):
        self._storage._setitem(index, value)

class _array_of_unknown_length(_parentable_mixin, lltype._parentable):
    _kind = "array"
    __slots__ = ()

    def getbounds(self):
        # we have no clue, so we allow whatever index
        return 0, sys.maxint

    def getitem(self, index, uninitialized_ok=False):
        return self._storage._getitem(index, boundscheck=False)

    def setitem(self, index, value):
        self._storage._setitem(index, value, boundscheck=False)

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
        if not llobj:   # NULL pointer
            return get_ctypes_type(T)()

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

        if container._storage is None:
            raise RuntimeError("attempting to pass a freed structure to C")
        if container._storage is True:
            # container has regular lltype storage, convert it to ctypes
            if isinstance(T.TO, lltype.Struct):
                convert_struct(container)
            elif isinstance(T.TO, lltype.Array):
                convert_array(container)
            else:
                raise NotImplementedError(T)
        storage = container._storage
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
        if not cobj:   # NULL pointer
            return lltype.nullptr(T.TO)
        if isinstance(T.TO, lltype.Struct):
            # XXX var-sized structs
            container = lltype._struct(T.TO)
            add_storage(container, _struct_mixin, cobj.contents)
            remove_regular_struct_content(container)
        elif isinstance(T.TO, lltype.Array):
            if T.TO._hints.get('nolength', False):
                container = _array_of_unknown_length(T.TO)
                container._storage = cobj.contents
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
    elif T is not lltype.Signed:
        from pypy.rpython.lltypesystem import rffi
        try:
            inttype = rffi.platform.numbertype_to_rclass[T]
        except KeyError:
            llobj = cobj
        else:
            llobj = inttype(cobj)
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

def force_cast(RESTYPE, value):
    """Cast a value to a result type, trying to use the same rules as C."""
    TYPE1 = lltype.typeOf(value)
    cvalue = lltype2ctypes(value)
    cresulttype = get_ctypes_type(RESTYPE)
    if isinstance(TYPE1, lltype.Ptr):
        if isinstance(RESTYPE, lltype.Ptr):
            # shortcut: ptr->ptr cast
            cptr = ctypes.cast(cvalue, cresulttype)
            return ctypes2lltype(RESTYPE, cptr)
        # first cast the input pointer to an integer
        cvalue = ctypes.c_void_p(cvalue).value
    elif isinstance(cvalue, (str, unicode)):
        cvalue = ord(cvalue)     # character -> integer

    if not isinstance(cvalue, (int, long)):
        raise NotImplementedError("casting %r to %r" % (TYPE1, RESTYPE))

    if isinstance(RESTYPE, lltype.Ptr):
        cvalue = ctypes.cast(ctypes.c_void_p(cvalue), cresulttype)
    else:
        cvalue = cresulttype(cvalue).value   # mask high bits off if needed
    return ctypes2lltype(RESTYPE, cvalue)

class ForceCastEntry(ExtRegistryEntry):
    _about_ = force_cast

    def compute_result_annotation(self, s_RESTYPE, s_value):
        assert s_RESTYPE.is_constant()
        RESTYPE = s_RESTYPE.const
        return annmodel.lltype_to_annotation(RESTYPE)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        s_RESTYPE = hop.args_s[0]
        assert s_RESTYPE.is_constant()
        RESTYPE = s_RESTYPE.const
        v_arg = hop.inputarg(hop.args_r[1], arg=1)
        TYPE1 = v_arg.concretetype
        return gen_cast(hop.llops, RESTYPE, v_arg)
