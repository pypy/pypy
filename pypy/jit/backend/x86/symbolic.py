import ctypes
from pypy.rpython.lltypesystem import lltype, ll2ctypes, llmemory
from pypy.rlib.objectmodel import specialize

@specialize.memo()
def get_field_token(STRUCT, fieldname, translate_support_code):
    if translate_support_code:
        return (llmemory.offsetof(STRUCT, fieldname),
                get_size(getattr(STRUCT, fieldname), True))
    cstruct = ll2ctypes.get_ctypes_type(STRUCT)
    cfield = getattr(cstruct, fieldname)
    return (cfield.offset, cfield.size)

@specialize.memo()
def get_size(TYPE, translate_support_code):
    if translate_support_code:
        if TYPE._is_varsize():
            return llmemory.sizeof(TYPE, 0)
        return llmemory.sizeof(TYPE)
    ctype = ll2ctypes.get_ctypes_type(TYPE)
    return ctypes.sizeof(ctype)

@specialize.memo()
def get_array_token(T, translate_support_code):
    # T can be an array or a var-sized structure
    if translate_support_code:
        basesize = llmemory.sizeof(T, 0)
        if isinstance(T, lltype.Struct):
            SUBARRAY = getattr(T, T._arrayfld)
            itemsize = llmemory.sizeof(SUBARRAY.OF)
            ofs_length = (llmemory.offsetof(T, T._arrayfld) +
                          llmemory.ArrayLengthOffset(SUBARRAY))
        else:
            itemsize = llmemory.sizeof(T.OF)
            ofs_length = llmemory.ArrayLengthOffset(T)
    else:
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

