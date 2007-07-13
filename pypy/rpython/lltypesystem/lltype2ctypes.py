import ctypes
from pypy.rpython.lltypesystem import lltype


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
                getattr(bigstruct, S._arrayfld).length = n
                return bigstruct
        _malloc = classmethod(_malloc)

        def _getattr(self, field_name):
            cobj = getattr(self, field_name)
            return ctypes2lltype(cobj)

        def _setattr(self, field_name, value):
            cobj = lltype2ctypes(value)
            setattr(self, field_name, cobj)

    CStruct.__name__ = 'ctypes_%s' % (S,)
    return CStruct

def build_ctypes_array(A, max_n=0):
    assert max_n >= 0
    ITEM = A.OF
    ctypes_item = get_ctypes_type(ITEM)

    class CArray(ctypes.Structure):
        _fields_ = [('length', ctypes.c_int),
                    ('items',  max_n * ctypes_item)]

        def _malloc(cls, n=None):
            if not isinstance(n, int):
                raise TypeError, "array length must be an int"
            biggercls = build_ctypes_array(A, n)
            bigarray = biggercls()
            bigarray.length = n
            return bigarray
        _malloc = classmethod(_malloc)

        def _getitem(self, index):
            cobj = self.items[index]
            return ctypes2lltype(cobj)

        def _setitem(self, index, value):
            cobj = lltype2ctypes(value)
            self.items[index] = cobj

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

def lltype2ctypes(llobj):
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
        return ctypes.pointer(container._ctypes_storage)
    return llobj

def ctypes2lltype(cobj):
    return cobj
