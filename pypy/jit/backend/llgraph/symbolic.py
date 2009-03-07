import ctypes
from pypy.rpython.lltypesystem import lltype, rffi, rclass


Size2Type = [None]
Type2Size = {}

def get_size(TYPE):
    try:
        return Type2Size[TYPE]
    except KeyError:
        size = len(Size2Type)
        Size2Type.append(TYPE)
        Type2Size[TYPE] = size
        return size

TokenToField = [None]
FieldToToken = {}

def get_field_token(STRUCT, fieldname):
    try:
        return FieldToToken[STRUCT, fieldname]
    except KeyError:
        token = (len(TokenToField), get_size(getattr(STRUCT, fieldname)))
        TokenToField.append((STRUCT, fieldname))
        FieldToToken[STRUCT, fieldname] = token
        return token
get_field_token(rclass.OBJECT, 'typeptr')     # force the index 1 for this

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
