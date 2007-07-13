import sys
import ctypes
from pypy.rpython.lltypesystem import lltype
from pypy.tool.uid import fixid

_Ctypes_PointerType = type(ctypes.POINTER(ctypes.c_int))

def uaddressof(obj):
    return fixid(ctypes.addressof(obj))

# ____________________________________________________________

_allocated = []

_ctypes_cache = {
    lltype.Signed: ctypes.c_long,
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

        def malloc(cls, n=None):
            if S._arrayfld is None:
                if n is not None:
                    raise TypeError("%r is not variable-sized" % (S,))
                storage = cls()
                _allocated.append(storage)
                return _ctypes_struct(S, storage)
            else:
                if n is None:
                    raise TypeError("%r is variable-sized" % (S,))
                biggercls = build_ctypes_struct(S, n)
                bigstruct = biggercls()
                _allocated.append(bigstruct)
                getattr(bigstruct, S._arrayfld).length = n
                return _ctypes_struct(S, bigstruct)
        malloc = classmethod(malloc)

    CStruct.__name__ = 'ctypes_%s' % (S,)
    return CStruct

def build_ctypes_array(A, max_n=0):
    assert max_n >= 0
    ITEM = A.OF
    ctypes_item = get_ctypes_type(ITEM)

    class CArray(ctypes.Structure):
        _fields_ = [('length', ctypes.c_int),
                    ('items',  max_n * ctypes_item)]

        def malloc(cls, n=None):
            if not isinstance(n, int):
                raise TypeError, "array length must be an int"
            biggercls = build_ctypes_array(A, n)
            bigarray = biggercls()
            _allocated.append(bigarray)
            bigarray.length = n
            return _ctypes_array(A, bigarray)
        malloc = classmethod(malloc)

    CArray.__name__ = 'ctypes_%s*%d' % (A, max_n)
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

def ctypes2lltype(val, RESTYPE):
    if isinstance(RESTYPE, lltype.Struct):
        return _ctypes_struct(RESTYPE, val)
    if isinstance(RESTYPE, lltype.Array):
        return _ctypes_array(RESTYPE, val)
    if isinstance(RESTYPE, lltype.Ptr):
        if isinstance(RESTYPE.TO, lltype.Array):
            ArrayType = build_ctypes_array(RESTYPE.TO,
                                           max_n=val.contents.length)
            val = ctypes.cast(val, ctypes.POINTER(ArrayType))
        obj = ctypes2lltype(val.contents, RESTYPE.TO)
        return lltype._ptr(RESTYPE, obj, solid=True)
    return val

def lltype2ctypes(val):
    T = lltype.typeOf(val)
    if isinstance(T, lltype.Ptr):
        return val._obj._convert_to_ctypes_pointer()
    return val


class _ctypes_parentable(lltype._parentable):

    __slots__ = ('_ctypes_storage',)

    def __init__(self, TYPE, ctypes_storage):
        lltype._parentable.__init__(self, TYPE)
        self._ctypes_storage = ctypes_storage

    def _free(self):
        # XXX REALLY SLOW!
        myaddress = ctypes.addressof(self._ctypes_storage)
        for i, obj in enumerate(_allocated):
            if ctypes.addressof(obj) == myaddress:
                # found it
                del _allocated[i]
                lltype._parentable._free(self)
                break
        else:
            raise RuntimeError("lltype.free() on a pointer that was not "
                               "obtained by lltype.malloc()")

    def _convert_to_ctypes_pointer(self):
        if self._TYPE._is_varsize():
            PtrType = ctypes.POINTER(get_ctypes_type(self._TYPE))
            return ctypes.cast(ctypes.pointer(self._ctypes_storage), PtrType)
        else:
            return ctypes.pointer(self._ctypes_storage)


class _ctypes_struct(_ctypes_parentable):
    _kind = "structure"
    __slots__ = ()

    def __init__(self, TYPE, ctypes_storage):
        _ctypes_parentable.__init__(self, TYPE, ctypes_storage)
        if TYPE._arrayfld is not None:
            array = getattr(ctypes_storage, TYPE._arrayfld)
            assert array.length == len(array.items)

    def __repr__(self):
        return '<ctypes struct %s at 0x%x>' % (
            self._TYPE._name,
            uaddressof(self._ctypes_storage))

    def __setattr__(self, field_name, value):
        if field_name.startswith('_'):
            lltype._parentable.__setattr__(self, field_name, value)
        else:
            setattr(self._ctypes_storage, field_name, lltype2ctypes(value))

    def _getattr(self, field_name, uninitialized_ok=False):
        return getattr(self, field_name)

    def __getattr__(self, field_name):
        if field_name.startswith('_'):
            return lltype._parentable.__getattr__(self, field_name)
        else:
            return ctypes2lltype(getattr(self._ctypes_storage, field_name),
                                 getattr(self._TYPE, field_name))

class _ctypes_array(_ctypes_parentable):
    _kind = "array"
    __slots__ = ()

    def __init__(self, TYPE, ctypes_storage):
        _ctypes_parentable.__init__(self, TYPE, ctypes_storage)
        assert ctypes_storage.length == len(ctypes_storage.items)

    def __repr__(self):
        return '<ctypes array at 0x%x>' % (
            uaddressof(self._ctypes_storage),)

    def getlength(self):
        length = self._ctypes_storage.length
        assert length == len(self._ctypes_storage.items)
        return length

    def getbounds(self):
        return 0, self.getlength()

    def getitem(self, index):
        return ctypes2lltype(self._ctypes_storage.items[index],
                             self._TYPE.OF)

# ____________________________________________________________

def malloc(T, n=None, flavor='gc', immortal=False):
    # XXX for now, let's only worry about raw malloc
    assert flavor == 'raw'
    assert T._gckind == 'raw'
    assert isinstance(T, (lltype.Struct, lltype.Array))
    cls = get_ctypes_type(T)
    container = cls.malloc(n)
    return lltype._ptr(lltype.Ptr(T), container, solid=True)

def getobjcount():
    return len(_allocated)
