import ctypes
from pypy.rpython.lltypesystem import lltype, ll2ctypes
from pypy.rlib.objectmodel import specialize

@specialize.memo()
def get_field_token(STRUCT, fieldname):
    cstruct = ll2ctypes.get_ctypes_type(STRUCT)
    cfield = getattr(cstruct, fieldname)
    return (cfield.offset, cfield.size)

@specialize.memo()
def get_size(TYPE):
    ctype = ll2ctypes.get_ctypes_type(TYPE)
    return ctypes.sizeof(ctype)

@specialize.memo()
def get_array_token(T):
    # T can be an array or a var-sized structure
    if isinstance(T, lltype.Struct):
        assert T._arrayfld is not None, "%r is not variable-sized" % (T,)
        cstruct = ll2ctypes.get_ctypes_type(T)
        cfield = getattr(cstruct, T._arrayfld)
        before_array_part = cfield.offset
        T = getattr(T, T._arrayfld)
    else:
        before_array_part = 0
    carray = ll2ctypes.get_ctypes_type(T)
    assert carray.length.size == 4
    ofs_length = before_array_part + carray.length.offset
    basesize = before_array_part + carray.items.offset
    carrayitem = ll2ctypes.get_ctypes_type(T.OF)
    itemsize = ctypes.sizeof(carrayitem)
    return basesize, itemsize, ofs_length

