import ctypes
from pypy.rpython.lltypesystem import lltype, ll2ctypes, llmemory, rffi
from pypy.rlib.objectmodel import specialize
from pypy.rlib.unroll import unrolling_iterable

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
def get_size_of_ptr(translate_support_code):
    return get_size(llmemory.GCREF, translate_support_code)

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
        assert carray.length.size == WORD
        ofs_length = before_array_part + carray.length.offset
        basesize = before_array_part + carray.items.offset
        carrayitem = ll2ctypes.get_ctypes_type(T.OF)
        itemsize = ctypes.sizeof(carrayitem)
    return basesize, itemsize, ofs_length

# ____________________________________________________________

WORD         = get_size(lltype.Signed, False)
SIZEOF_CHAR  = get_size(lltype.Char, False)
SIZEOF_SHORT = get_size(rffi.SHORT, False)
SIZEOF_INT   = get_size(rffi.INT, False)
SIZEOF_FLOAT = get_size(lltype.Float, False)

unroll_basic_sizes = unrolling_iterable([(lltype.Signed, WORD),
                                         (lltype.Char,   SIZEOF_CHAR),
                                         (rffi.SHORT,    SIZEOF_SHORT),
                                         (rffi.INT,      SIZEOF_INT)])
# does not contain Float ^^^ which must be special-cased
