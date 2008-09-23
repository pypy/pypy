import sys

try:
    import ctypes
    import ctypes.util
except ImportError:
    ctypes = None

import os
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.extfunc import ExtRegistryEntry
from pypy.rlib.objectmodel import Symbolic
from pypy.tool.uid import fixid
from pypy.tool.tls import tlsobject
from pypy.rlib.rarithmetic import r_uint, r_singlefloat
from pypy.annotation import model as annmodel

def uaddressof(obj):
    return fixid(ctypes.addressof(obj))


_ctypes_cache = {}
_eci_cache = {}

def _setup_ctypes_cache():
    from pypy.rpython.lltypesystem import rffi
    _ctypes_cache.update({
        lltype.Signed:   ctypes.c_long,
        lltype.Unsigned: ctypes.c_ulong,
        lltype.Char:     ctypes.c_ubyte,
        rffi.DOUBLE:     ctypes.c_double,
        rffi.FLOAT:      ctypes.c_float,
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
        lltype.UniChar:  ctypes.c_uint,
        })

def build_ctypes_struct(S, delayed_builders, max_n=None):
    def builder():
        # called a bit later to fill in _fields_
        # (to handle recursive structure pointers)
        fields = []
        for fieldname in S._names:
            FIELDTYPE = S._flds[fieldname]
            if max_n is not None and fieldname == S._arrayfld:
                cls = get_ctypes_array_of_size(FIELDTYPE, max_n)
            else:
                cls = get_ctypes_type(FIELDTYPE)
            fields.append((fieldname, cls))
        CStruct._fields_ = fields

    class CStruct(ctypes.Structure):
        # no _fields_: filled later by builder()

        def _malloc(cls, n=None):
            if S._arrayfld is None:
                if n is not None:
                    raise TypeError("%r is not variable-sized" % (S,))
                storage = cls()
                return storage
            else:
                if n is None:
                    raise TypeError("%r is variable-sized" % (S,))
                biggercls = build_ctypes_struct(S, None, n)
                bigstruct = biggercls()
                array = getattr(bigstruct, S._arrayfld)
                if hasattr(array, 'length'):
                    array.length = n
                return bigstruct
        _malloc = classmethod(_malloc)

    CStruct.__name__ = 'ctypes_%s' % (S,)
    if max_n is not None:
        CStruct._normalized_ctype = get_ctypes_type(S)
        builder()    # no need to be lazy here
    else:
        delayed_builders.append(builder)
    return CStruct

def build_ctypes_array(A, delayed_builders, max_n=0):
    assert max_n >= 0
    ITEM = A.OF
    ctypes_item = get_ctypes_type(ITEM, delayed_builders)

    class CArray(ctypes.Structure):
        if not A._hints.get('nolength'):
            _fields_ = [('length', ctypes.c_int),
                        ('items',  max_n * ctypes_item)]
        else:
            _fields_ = [('items',  max_n * ctypes_item)]

        def _malloc(cls, n=None):
            if not isinstance(n, int):
                raise TypeError, "array length must be an int"
            biggercls = get_ctypes_array_of_size(A, n)
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
            if isinstance(ITEM, lltype.ContainerType):
                return ctypes2lltype(lltype.Ptr(ITEM), ctypes.pointer(cobj))
            else:
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

def get_ctypes_array_of_size(FIELDTYPE, max_n):
    if max_n > 0:
        # no need to cache the results in this case, because the exact
        # type is never seen - the array instances are cast to the
        # array's _normalized_ctype, which is always the same.
        return build_ctypes_array(FIELDTYPE, None, max_n)
    else:
        return get_ctypes_type(FIELDTYPE)

def get_ctypes_type(T, delayed_builders=None):
    try:
        return _ctypes_cache[T]
    except KeyError:
        toplevel = delayed_builders is None
        if toplevel:
            delayed_builders = []
        cls = build_new_ctypes_type(T, delayed_builders)
        if T not in _ctypes_cache:
            _ctypes_cache[T] = cls
        else:
            # check for buggy recursive structure logic
            assert _ctypes_cache[T] is cls
        if toplevel:
            complete_builders(delayed_builders)
        return cls

def build_new_ctypes_type(T, delayed_builders):
    if isinstance(T, lltype.Ptr):
        if isinstance(T.TO, lltype.FuncType):
            argtypes = [get_ctypes_type(ARG) for ARG in T.TO.ARGS]
            if T.TO.RESULT is lltype.Void:
                restype = None
            else:
                restype = get_ctypes_type(T.TO.RESULT)
            return ctypes.CFUNCTYPE(restype, *argtypes)
        else:
            return ctypes.POINTER(get_ctypes_type(T.TO, delayed_builders))
    elif isinstance(T, lltype.Struct):
        return build_ctypes_struct(T, delayed_builders)
    elif isinstance(T, lltype.Array):
        return build_ctypes_array(T, delayed_builders)
    elif isinstance(T, lltype.OpaqueType):
        if T.hints.get('external', None) != 'C':
            raise TypeError("%s is not external" % T)
        return ctypes.c_char * T.hints['getsize']()
    else:
        _setup_ctypes_cache()
        if T in _ctypes_cache:
            return _ctypes_cache[T]
        raise NotImplementedError(T)

def complete_builders(delayed_builders):
    while delayed_builders:
        delayed_builders.pop()()


def convert_struct(container, cstruct=None):
    STRUCT = container._TYPE
    if cstruct is None:
        # if 'container' is an inlined substructure, convert the whole
        # bigger structure at once
        parent, parentindex = lltype.parentlink(container)
        if parent is not None:
            convert_struct(parent)
            return
        # regular case: allocate a new ctypes Structure of the proper type
        cls = get_ctypes_type(STRUCT)
        if STRUCT._arrayfld:
            n = len(getattr(container, STRUCT._arrayfld).items)
        else:
            n = None
        cstruct = cls._malloc(n)
    add_storage(container, _struct_mixin, cstruct)
    for field_name in STRUCT._names:
        FIELDTYPE = getattr(STRUCT, field_name)
        field_value = getattr(container, field_name)
        if not isinstance(FIELDTYPE, lltype.ContainerType):
            # regular field
            setattr(cstruct, field_name, lltype2ctypes(field_value))
        else:
            # inlined substructure/subarray
            if isinstance(FIELDTYPE, lltype.Struct):
                csubstruct = getattr(cstruct, field_name)
                convert_struct(field_value, csubstruct)
            else:
                csubarray = getattr(cstruct, field_name)
                convert_array(field_value, csubarray)
                #raise NotImplementedError('inlined field', FIELDTYPE)
    remove_regular_struct_content(container)

def remove_regular_struct_content(container):
    STRUCT = container._TYPE
    for field_name in STRUCT._names:
        FIELDTYPE = getattr(STRUCT, field_name)
        if not isinstance(FIELDTYPE, lltype.ContainerType):
            delattr(container, field_name)

def convert_array(container, carray=None):
    ARRAY = container._TYPE
    cls = get_ctypes_type(ARRAY)
    if carray is None:
        carray = cls._malloc(container.getlength())
    add_storage(container, _array_mixin, carray)
    if not isinstance(ARRAY.OF, lltype.ContainerType):
        # fish that we have enough space
        ctypes_array = ctypes.cast(carray.items,
                                   ctypes.POINTER(carray.items._type_))
        for i in range(container.getlength()):
            item_value = container.items[i]    # fish fish
            ctypes_array[i] = lltype2ctypes(item_value)
        remove_regular_array_content(container)
    else:
        assert isinstance(ARRAY.OF, lltype.Struct)
        for i in range(container.getlength()):
            item_ptr = container.items[i]    # fish fish
            convert_struct(item_ptr, carray.items[i])

def remove_regular_array_content(container):
    for i in range(container.getlength()):
        container.items[i] = None

def struct_use_ctypes_storage(container, ctypes_storage):
    STRUCT = container._TYPE
    assert isinstance(STRUCT, lltype.Struct)
    add_storage(container, _struct_mixin, ctypes_storage)
    remove_regular_struct_content(container)
    for field_name in STRUCT._names:
        FIELDTYPE = getattr(STRUCT, field_name)
        if isinstance(FIELDTYPE, lltype.Array):
            convert_array(getattr(container, field_name),
                          getattr(ctypes_storage, field_name))
        elif isinstance(FIELDTYPE, lltype.ContainerType):
            struct_use_ctypes_storage(getattr(container, field_name),
                                      getattr(ctypes_storage, field_name))

# ____________________________________________________________
# Ctypes-aware subclasses of the _parentable classes

ALLOCATED = {}     # mapping {address: _container}

def get_common_subclass(cls1, cls2, cache={}):
    """Return a unique subclass with (cls1, cls2) as bases."""
    try:
        return cache[cls1, cls2]
    except KeyError:
        subcls = type('_ctypes_%s' % (cls1.__name__,),
                      (cls1, cls2),
                      {'__slots__': ()})
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

    def _ctypes_storage_was_allocated(self):
        addr = ctypes.addressof(self._storage)
        if addr in ALLOCATED:
            raise Exception("internal ll2ctypes error - "
                            "double conversion from lltype to ctypes?")
        # XXX don't store here immortal structures
        ALLOCATED[addr] = self

    def _free(self):
        self._check()   # no double-frees
        # allow the ctypes object to go away now
        addr = ctypes.addressof(self._storage)
        try:
            del ALLOCATED[addr]
        except KeyError:
            raise Exception("invalid free() - data already freed or "
                            "not allocated from RPython at all")
        self._storage = None

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

def _find_parent(llobj):
    parent, parentindex = lltype.parentlink(llobj)
    if parent is None:
        return llobj, 0
    next_p, next_i = _find_parent(parent)
    if isinstance(parentindex, int):
        c_tp = get_ctypes_type(lltype.typeOf(parent))
        sizeof = ctypes.sizeof(get_ctypes_type(lltype.typeOf(parent).OF))
        ofs = c_tp.items.offset + parentindex * sizeof
        return next_p, next_i + ofs
    else:
        c_tp = get_ctypes_type(lltype.typeOf(parent))
        ofs = getattr(c_tp, parentindex).offset
        return next_p, next_i + ofs


# XXX THIS IS A HACK XXX
# ctypes does not keep callback arguments alive. So we do. Forever
# we need to think deeper how to approach this problem
# additionally, this adds mess to __del__ "semantics"
_all_callbacks = []

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
                res = ctypes_func_type(callback)
                _all_callbacks.append(res)
                return res

        if T.TO._gckind != 'raw' and not T.TO._hints.get('callback', None):
            raise Exception("can only pass 'raw' data structures to C, not %r"
                            % (T.TO._gckind,))

        index = 0
        if isinstance(container, lltype._subarray):
            topmost, index = _find_parent(container)
            container = topmost
        if container._storage is None:
            raise RuntimeError("attempting to pass a freed structure to C")
        if container._storage is True:
            # container has regular lltype storage, convert it to ctypes
            if isinstance(T.TO, lltype.Struct):
                convert_struct(container)
            elif isinstance(T.TO, lltype.Array):
                convert_array(container)
            elif isinstance(T.TO, lltype.OpaqueType):
                cbuf = ctypes.create_string_buffer(T.TO.hints['getsize']())
                add_storage(container, _parentable_mixin, cbuf)
            else:
                raise NotImplementedError(T)
            container._ctypes_storage_was_allocated()
        storage = container._storage
        p = ctypes.pointer(storage)
        if index:
            p = ctypes.cast(p, ctypes.c_void_p)
            p = ctypes.c_void_p(p.value + index)
            c_tp = get_ctypes_type(T.TO)
            storage._normalized_ctype = c_tp
        if normalize and getattr(T.TO, '_arrayfld', None):
            # XXX doesn't cache
            c_tp = build_ctypes_struct(T.TO, [],
                         len(getattr(storage, T.TO._arrayfld).items))
            p = ctypes.cast(p, ctypes.POINTER(c_tp))
        elif normalize and hasattr(storage, '_normalized_ctype'):
            p = ctypes.cast(p, ctypes.POINTER(storage._normalized_ctype))
        return p

    if isinstance(llobj, Symbolic):
        if isinstance(llobj, llmemory.ItemOffset):
            llobj = ctypes.sizeof(get_ctypes_type(llobj.TYPE)) * llobj.repeat
        else:
            raise NotImplementedError(llobj)  # don't know about symbolic value

    if T is lltype.Char or T is lltype.UniChar:
        return ord(llobj)

    if T is lltype.SingleFloat:
        return ctypes.c_float(float(llobj))
    return llobj

def ctypes2lltype(T, cobj):
    """Convert the ctypes object 'cobj' to its lltype equivalent.
    'T' is the expected lltype type.
    """
    if isinstance(T, lltype.Ptr):
        if not cobj:   # NULL pointer
            return lltype.nullptr(T.TO)
        if isinstance(T.TO, lltype.Struct):
            if T.TO._arrayfld is not None:
                lgt = getattr(cobj.contents, T.TO._arrayfld).length
                container = lltype._struct(T.TO, lgt)
            else:
                container = lltype._struct(T.TO)
            struct_use_ctypes_storage(container, cobj.contents)
        elif isinstance(T.TO, lltype.Array):
            if T.TO._hints.get('nolength', False):
                container = _array_of_unknown_length(T.TO)
                container._storage = cobj.contents
            else:
                raise NotImplementedError("array with an explicit length")
        elif isinstance(T.TO, lltype.FuncType):
            _callable = get_ctypes_trampoline(T.TO, cobj)
            return lltype.functionptr(T.TO, getattr(cobj, '__name__', '?'),
                                      _callable=_callable)
        elif isinstance(T.TO, lltype.OpaqueType):
            container = lltype._opaque(T.TO)
        else:
            raise NotImplementedError(T)
        llobj = lltype._ptr(T, container, solid=True)
    elif T is lltype.Char:
        llobj = chr(cobj)
    elif T is lltype.UniChar:
        llobj = unichr(cobj)
    elif T is lltype.Signed:
        llobj = cobj
    elif T is lltype.SingleFloat:
        if isinstance(cobj, ctypes.c_float):
            cobj = cobj.value
        llobj = r_singlefloat(cobj)
    else:
        from pypy.rpython.lltypesystem import rffi
        try:
            inttype = rffi.platform.numbertype_to_rclass[T]
        except KeyError:
            llobj = cobj
        else:
            llobj = inttype(cobj)

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

if ctypes:
    def get_libc_name():
        if sys.platform == 'win32':
            # Parses sys.version and deduces the version of the compiler
            import distutils.msvccompiler
            version = distutils.msvccompiler.get_build_version()
            if version is None:
                # This logic works with official builds of Python.
                if sys.version_info < (2, 4):
                    clibname = 'msvcrt'
                else:
                    clibname = 'msvcr71'
            else:
                if version <= 6:
                    clibname = 'msvcrt'
                else:
                    clibname = 'msvcr%d' % (version * 10)

            # If python was built with in debug mode
            import imp
            if imp.get_suffixes()[0][0] == '_d.pyd':
                clibname += 'd'

            return clibname+'.dll'
        else:
            return ctypes.util.find_library('c')
        
    libc_name = get_libc_name()     # Make sure the name is determined during import, not at runtime
    standard_c_lib = ctypes.cdll.LoadLibrary(get_libc_name())

# ____________________________________________


def get_ctypes_callable(funcptr, calling_conv):
    if not ctypes:
        raise ImportError("ctypes is needed to use ll2ctypes")

    def get_on_lib(lib, elem):
        """ Wrapper to always use lib[func] instead of lib.func
        """
        try:
            return lib[elem]
        except AttributeError:
            pass
    
    old_eci = funcptr._obj.compilation_info
    funcname = funcptr._obj._name
    try:
        eci = _eci_cache[old_eci]
    except KeyError:
        eci = old_eci.compile_shared_lib()
        _eci_cache[old_eci] = eci

    libraries = list(eci.libraries + eci.frameworks)

    FUNCTYPE = lltype.typeOf(funcptr).TO
    if not libraries:
        cfunc = get_on_lib(standard_c_lib, funcname)
        # XXX magic: on Windows try to load the function from 'kernel32' too
        if cfunc is None and hasattr(ctypes, 'windll'):
            cfunc = get_on_lib(ctypes.windll.kernel32, funcname)
    else:
        cfunc = None
        for libname in libraries:
            libpath = ctypes.util.find_library(libname)
            if not libpath and os.path.isabs(libname):
                libpath = libname
            if libpath:
                dllclass = getattr(ctypes, calling_conv + 'dll')
                # urgh, cannot pass the flag to dllclass.LoadLibrary
                clib = dllclass._dlltype(libpath, ctypes.RTLD_GLOBAL)
                cfunc = get_on_lib(clib, funcname)
                if cfunc is not None:
                    break

    if cfunc is None:
        # function name not found in any of the libraries
        if not libraries:
            place = 'the standard C library (missing libraries=...?)'
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

class LL2CtypesCallable(object):
    # a special '_callable' object that invokes ctypes

    def __init__(self, FUNCTYPE, calling_conv):
        self.FUNCTYPE = FUNCTYPE
        self.calling_conv = calling_conv
        self.trampoline = None
        #self.funcptr = ...  set later

    def __call__(self, *argvalues):
        if self.trampoline is None:
            # lazily build the corresponding ctypes function object
            cfunc = get_ctypes_callable(self.funcptr, self.calling_conv)
            self.trampoline = get_ctypes_trampoline(self.FUNCTYPE, cfunc)
        # perform the call
        return self.trampoline(*argvalues)

def get_ctypes_trampoline(FUNCTYPE, cfunc):
    RESULT = FUNCTYPE.RESULT
    container_arguments = []
    for i in range(len(FUNCTYPE.ARGS)):
        if isinstance(FUNCTYPE.ARGS[i], lltype.ContainerType):
            container_arguments.append(i)
    def invoke_via_ctypes(*argvalues):
        cargs = [lltype2ctypes(value) for value in argvalues]
        for i in container_arguments:
            cargs[i] = cargs[i].contents
        _restore_c_errno()
        cres = cfunc(*cargs)
        _save_c_errno()
        return ctypes2lltype(RESULT, cres)
    return invoke_via_ctypes

def force_cast(RESTYPE, value):
    """Cast a value to a result type, trying to use the same rules as C."""
    if not isinstance(RESTYPE, lltype.LowLevelType):
        raise TypeError("rffi.cast() first arg should be a TYPE")
    if isinstance(value, llmemory.fakeaddress):
        value = value.ptr
    TYPE1 = lltype.typeOf(value)
    cvalue = lltype2ctypes(value)
    cresulttype = get_ctypes_type(RESTYPE)
    if isinstance(TYPE1, lltype.Ptr):
        if isinstance(RESTYPE, lltype.Ptr):
            # shortcut: ptr->ptr cast
            cptr = ctypes.cast(cvalue, cresulttype)
            return ctypes2lltype(RESTYPE, cptr)
        # first cast the input pointer to an integer
        cvalue = ctypes.cast(cvalue, ctypes.c_void_p).value
        if cvalue is None:
            cvalue = 0
    elif isinstance(cvalue, (str, unicode)):
        cvalue = ord(cvalue)     # character -> integer

    if not isinstance(cvalue, (int, long)):
        raise NotImplementedError("casting %r to %r" % (TYPE1, RESTYPE))

    if isinstance(RESTYPE, lltype.Ptr):
        # upgrade to a more recent ctypes (e.g. 1.0.2) if you get
        # an OverflowError on the following line.
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
        return hop.genop('force_cast', [v_arg], resulttype = RESTYPE)

def typecheck_ptradd(T):
    # --- ptradd() is only for pointers to non-GC, no-length arrays.
    assert isinstance(T, lltype.Ptr)
    assert isinstance(T.TO, lltype.Array)
    assert T.TO._hints.get('nolength')

def force_ptradd(ptr, n):
    """'ptr' must be a pointer to an array.  Equivalent of 'ptr + n' in
    C, i.e. gives a pointer to the n'th item of the array.  The type of
    the result is again a pointer to an array, the same as the type of
    'ptr'.
    """
    T = lltype.typeOf(ptr)
    typecheck_ptradd(T)
    ctypes_item_type = get_ctypes_type(T.TO.OF)
    ctypes_arrayptr_type = get_ctypes_type(T)
    cptr = lltype2ctypes(ptr)
    baseaddr = ctypes.addressof(cptr.contents.items)
    addr = baseaddr + n * ctypes.sizeof(ctypes_item_type)
    cptr = ctypes.cast(ctypes.c_void_p(addr), ctypes_arrayptr_type)
    return ctypes2lltype(T, cptr)

class ForceCastEntry(ExtRegistryEntry):
    _about_ = force_ptradd

    def compute_result_annotation(self, s_ptr, s_n):
        assert isinstance(s_n, annmodel.SomeInteger)
        assert isinstance(s_ptr, annmodel.SomePtr)
        typecheck_ptradd(s_ptr.ll_ptrtype)
        return annmodel.lltype_to_annotation(s_ptr.ll_ptrtype)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        v_ptr, v_n = hop.inputargs(hop.args_r[0], lltype.Signed)
        return hop.genop('direct_ptradd', [v_ptr, v_n],
                         resulttype = v_ptr.concretetype)

# ____________________________________________________________
# errno

# this saves in a thread-local way the "current" value that errno
# should have in C.  We have to save it away from one external C function
# call to the next.  Otherwise a non-zero value left behind will confuse
# CPython itself a bit later, and/or CPython will stamp on it before we
# try to inspect it via rposix.get_errno().
TLS = tlsobject()

# helpers to save/restore the C-level errno -- platform-specific because
# ctypes doesn't just do the right thing and expose it directly :-(
def _where_is_errno():
    raise NotImplementedError("don't know how to get the C-level errno!")

def _save_c_errno():
    errno_p = _where_is_errno()
    TLS.errno = errno_p.contents.value
    errno_p.contents.value = 0

def _restore_c_errno():
    if hasattr(TLS, 'errno'):
        _where_is_errno().contents.value = TLS.errno

if ctypes:
    if sys.platform == 'win32':
        standard_c_lib._errno.restype = ctypes.POINTER(ctypes.c_int)
        def _where_is_errno():
            return standard_c_lib._errno()

    elif sys.platform in ('linux2', 'freebsd6'):
        standard_c_lib.__errno_location.restype = ctypes.POINTER(ctypes.c_int)
        def _where_is_errno():
            return standard_c_lib.__errno_location()

    elif sys.platform == 'darwin':
        standard_c_lib.__error.restype = ctypes.POINTER(ctypes.c_int)
        def _where_is_errno():
            return standard_c_lib.__error()
