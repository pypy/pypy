import ctypes, sys, weakref
from pypy.rpython.lltypesystem.lltype import Signed, Struct, GcStruct, Ptr
from pypy.rpython.lltypesystem.lltype import ContainerType, Array, GcArray
from pypy.rpython.lltypesystem.lltype import typeOf, castable

_Ctypes_PointerType = type(ctypes.POINTER(ctypes.c_int))


def cast_pointer(PTRTYPE, ptr):
    CURTYPE = typeOf(ptr)
    if not isinstance(CURTYPE, Ptr) or not isinstance(PTRTYPE, Ptr):
        raise TypeError, "can only cast pointers to other pointers"
    return ptr._cast_to(PTRTYPE)


class _parentable(ctypes.Structure):   # won't work with Union
    __slots__ = ()

# ____________________________________________________________

_ctypes_cache = {
    Signed: ctypes.c_long,
    }

def _build_ctypes_struct(S, max_n=None):
    fields = []
    for fieldname in S._names:
        FIELDTYPE = S._flds[fieldname]
        if max_n is not None and fieldname == S._arrayfld:
            cls = _build_ctypes_array(FIELDTYPE, max_n)
        else:
            cls = _get_ctypes_type(FIELDTYPE)
        fields.append((fieldname, cls))

    class CStruct(_parentable):
        _fields_ = fields
        _TYPE    = S

        def malloc(cls, n=None):
            S = cls._TYPE
            if S._arrayfld is None:
                if n is not None:
                    raise TypeError("%r is not variable-sized" % (S,))
                return ctypes.pointer(cls())
            else:
                if n is None:
                    raise TypeError("%r is variable-sized" % (S,))
                smallercls = _build_ctypes_struct(S, n)
                smallstruct = smallercls()
                getattr(smallstruct, S._arrayfld).length = n
                structptr = ctypes.cast(ctypes.pointer(smallstruct),
                                        ctypes.POINTER(cls))
                return structptr
        malloc = classmethod(malloc)

    CStruct.__name__ = 'ctypes_%s' % (S,)
    return CStruct

def _build_ctypes_array(A, max_n=None):
    ITEM = A.OF
    ctypes_item = _get_ctypes_type(ITEM)
    if max_n is None:
        max_n = sys.maxint // ctypes.sizeof(ctypes_item)
        max_n //= 2   # XXX better safe than sorry about ctypes bugs

    class CArray(_parentable):
        _fields_ = [('length', ctypes.c_int),
                    ('items',  max_n * ctypes_item)]
        _TYPE    = A

        def malloc(cls, n=None):
            if not isinstance(n, int):
                raise TypeError, "array length must be an int"
            smallercls = _build_ctypes_array(cls._TYPE, n)
            smallarray = smallercls()
            smallarray.length = n
            arrayptr = ctypes.cast(ctypes.pointer(smallarray),
                                   ctypes.POINTER(cls))
            return arrayptr
        malloc = classmethod(malloc)

    CArray.__name__ = 'ctypes_%s' % (A,)
    return CArray

def _get_ctypes_type(T):
    try:
        return _ctypes_cache[T]
    except KeyError:
        if isinstance(T, Ptr):
            cls = ctypes.POINTER(_get_ctypes_type(T.TO))
        elif isinstance(T, Struct):
            cls = _build_ctypes_struct(T)
        elif isinstance(T, Array):
            cls = _build_ctypes_array(T)
        else:
            raise NotImplementedError(T)
        _ctypes_cache[T] = cls
        return cls

def _expose(val):
    if isinstance(type(val), _Ctypes_PointerType):
        val = val.contents
    T = typeOf(val)
    if isinstance(T, ContainerType):
        val = _ptr(ctypes.pointer(val))
    return val

def _lltype2ctypes(val):
    T = typeOf(val)
    if isinstance(T, Ptr):
        return val._storageptr
    return val

class _ptr(object):
    __slots__ = ['_storageptr', '_TYPE']

    def __init__(self, storageptr):
        assert isinstance(type(storageptr), _Ctypes_PointerType)
        _ptr._storageptr.__set__(self, storageptr)
        _ptr._TYPE.__set__(self, Ptr(type(storageptr)._type_._TYPE))

    def __getattr__(self, field_name):
        if isinstance(self._TYPE.TO, Struct):
            if field_name in self._TYPE.TO._flds:
                return _expose(getattr(self._storageptr.contents, field_name))
        raise AttributeError("%r instance has no field %r" % (self._TYPE.TO,
                                                              field_name))

    def __setattr__(self, field_name, value):
        if isinstance(self._TYPE.TO, Struct):
            if field_name in self._TYPE.TO._flds:
                setattr(self._storageptr.contents, field_name,
                        _lltype2ctypes(value))
                return
        raise AttributeError("%r instance has no field %r" % (self._TYPE.TO,
                                                              field_name))

    def __nonzero__(self):
        return bool(self._storageptr)

    def __len__(self):
        T = self._TYPE.TO
        if isinstance(T, Array):# ,FixedSizeArray)):
            #if self._T._hints.get('nolength', False):
            #    raise TypeError("%r instance has no length attribute" %
            #                        (self._T,))
            return self._storageptr.contents.length
        raise TypeError("%r instance is not an array" % (T,))

    def __getitem__(self, i):
        T = self._TYPE.TO
        if isinstance(T, Array):
            start, stop = 0, self._storageptr.contents.length
            if not (start <= i < stop):
                if isinstance(i, slice):
                    raise TypeError("array slicing not supported")
                raise IndexError("array index out of bounds")
            return _expose(self._storageptr.contents.items[i])
        raise TypeError("%r instance is not an array" % (T,))

    def _cast_to(self, PTRTYPE):
        CURTYPE = self._TYPE
        down_or_up = castable(PTRTYPE, CURTYPE)
        if down_or_up == 0:
            return self
        if not self: # null pointer cast
            return PTRTYPE._defl()
        WAAA
        if isinstance(self._obj, int):
            return _ptr(PTRTYPE, self._obj, solid=True)
        if down_or_up > 0:
            p = self
            while down_or_up:
                p = getattr(p, typeOf(p).TO._names[0])
                down_or_up -= 1
            return _ptr(PTRTYPE, p._obj, solid=self._solid)
        u = -down_or_up
        struc = self._obj
        while u:
            parent = struc._parentstructure()
            if parent is None:
                raise RuntimeError("widening to trash: %r" % self)
            PARENTTYPE = struc._parent_type
            if getattr(parent, PARENTTYPE._names[0]) is not struc:
                raise InvalidCast(CURTYPE, PTRTYPE) # xxx different exception perhaps?
            struc = parent
            u -= 1
        if PARENTTYPE != PTRTYPE.TO:
            raise RuntimeError("widening %r inside %r instead of %r" % (CURTYPE, PARENTTYPE, PTRTYPE.TO))
        return _ptr(PTRTYPE, struc, solid=self._solid)

# ____________________________________________________________

def malloc(T, n=None, immortal=False):
    if T._gckind != 'gc' and not immortal:# and flavor.startswith('gc'):
        raise TypeError, "gc flavor malloc of a non-GC non-immortal structure"
    if isinstance(T, (Struct, Array)):
        cls = _get_ctypes_type(T)
        return _ptr(cls.malloc(n))
    else:
        raise TypeError, "malloc for Structs and Arrays only"

def nullptr(T):
    cls = _get_ctypes_type(T)
    return _ptr(ctypes.POINTER(cls)())
