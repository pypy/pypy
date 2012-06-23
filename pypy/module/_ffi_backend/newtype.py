from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import ovfcheck

from pypy.module._ffi_backend import ctypeobj


def alignment(TYPE):
    S = lltype.Struct('aligncheck', ('x', lltype.Char), ('y', TYPE))
    return rffi.offsetof(S, 'y')

alignment_of_pointer = alignment(rffi.CCHARP)

# ____________________________________________________________


PRIMITIVE_TYPES = {}

def eptype(name, TYPE, ctypecls):
    PRIMITIVE_TYPES[name] = ctypecls, rffi.sizeof(TYPE), alignment(TYPE)

eptype("char",        lltype.Char,     ctypeobj.W_CTypePrimitiveChar)
eptype("signed char", rffi.SIGNEDCHAR, ctypeobj.W_CTypePrimitiveSigned)
eptype("short",       rffi.SHORT,      ctypeobj.W_CTypePrimitiveSigned)
eptype("int",         rffi.INT,        ctypeobj.W_CTypePrimitiveSigned)
eptype("long",        rffi.LONG,       ctypeobj.W_CTypePrimitiveSigned)
eptype("long long",   rffi.LONGLONG,   ctypeobj.W_CTypePrimitiveSigned)
eptype("unsigned char",      rffi.UCHAR,    ctypeobj.W_CTypePrimitiveUnsigned)
eptype("unsigned short",     rffi.SHORT,    ctypeobj.W_CTypePrimitiveUnsigned)
eptype("unsigned int",       rffi.INT,      ctypeobj.W_CTypePrimitiveUnsigned)
eptype("unsigned long",      rffi.LONG,     ctypeobj.W_CTypePrimitiveUnsigned)
eptype("unsigned long long", rffi.LONGLONG, ctypeobj.W_CTypePrimitiveUnsigned)
eptype("float",  rffi.FLOAT,  ctypeobj.W_CTypePrimitiveFloat)
eptype("double", rffi.DOUBLE, ctypeobj.W_CTypePrimitiveFloat)

@unwrap_spec(name=str)
def new_primitive_type(space, name):
    try:
        ctypecls, size, align = PRIMITIVE_TYPES[name]
    except KeyError:
        raise OperationError(space.w_KeyError, space.wrap(name))
    ctype = ctypecls(space, size, name, len(name), align)
    return ctype

# ____________________________________________________________

@unwrap_spec(ctype=ctypeobj.W_CType)
def new_pointer_type(space, ctype):
    ctypeptr = ctypeobj.W_CTypePointer(space, ctype)
    return ctypeptr

# ____________________________________________________________

@unwrap_spec(ctptr=ctypeobj.W_CType)
def new_array_type(space, ctptr, w_length):
    if not isinstance(ctptr, ctypeobj.W_CTypePointer):
        raise OperationError(space.w_TypeError,
                             space.wrap("first arg must be a pointer ctype"))
    ctitem = ctptr.ctitem
    if ctitem.size < 0:
        raise operationerrfmt(space.w_ValueError,
                              "array item of unknown size: '%s'",
                              ctitem.name)
    if space.is_w(w_length, space.w_None):
        length = -1
        arraysize = -1
        extra = '[]'
    else:
        length = space.getindex_w(w_length, space.w_OverflowError)
        if length < 0:
            raise OperationError(space.w_ValueError,
                                 space.wrap("negative array length"))
        try:
            arraysize = ovfcheck(length * ctitem.size)
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                space.wrap("array size would overflow a ssize_t"))
        extra = '[%d]' % length
    #
    ctypeptr = ctypeobj.W_CTypeArray(space, ctptr, length, arraysize, extra)
    return ctypeptr

# ____________________________________________________________

@unwrap_spec(name=str)
def new_struct_type(space, name):
    return ctypeobj.W_CTypeStruct(space, name)

@unwrap_spec(name=str)
def new_union_type(space, name):
    return ctypeobj.W_CTypeUnion(space, name)

@unwrap_spec(ctype=ctypeobj.W_CType, totalsize=int, totalalignment=int)
def complete_struct_or_union(space, ctype, w_fields, w_ignored=None,
                             totalsize=-1, totalalignment=-1):
    if (not isinstance(ctype, ctypeobj.W_CTypeStructOrUnion)
            or ctype.size >= 0):
        raise OperationError(space.w_TypeError,
                             space.wrap("first arg must be a non-initialized"
                                        " struct or union ctype"))

    is_union = isinstance(ctype, ctypeobj.W_CTypeUnion)
    maxsize = 1
    alignment = 1
    offset = 0
    fields_w = space.listview(w_fields)
    fields_list = []
    fields_dict = {}
    prev_bit_position = 0
    prev_field = None

    for w_field in fields_w:
        field_w = space.fixedview(w_field)
        if not (2 <= len(field_w) <= 4):
            raise OperationError(space.w_TypeError,
                                 space.wrap("bad field descr"))
        fname = space.str_w(field_w[0])
        ftype = space.interp_w(ctypeobj.W_CType, field_w[1])
        fbitsize = -1
        foffset = -1
        if len(field_w) > 2: fbitsize = space.int_w(field_w[2])
        if len(field_w) > 3: foffset = space.int_w(field_w[3])
        #
        if fname in fields_dict:
            raise operationerrfmt(space.w_KeyError,
                                  "duplicate field name '%s'", fname)
        #
        if ftype.size < 0:
            raise operationerrfmt(space.w_TypeError,
                    "field '%s.%s' has ctype '%s' of unknown size",
                                  ctype.name, fname, ftype.name)
        #
        falign = ftype.alignof()
        if alignment < falign:
            alignment = falign
        #
        if foffset < 0:
            # align this field to its own 'falign' by inserting padding
            offset = (offset + falign - 1) & ~(falign-1)
        else:
            offset = foffset
        #
        if fbitsize < 0 or (fbitsize == 8 * ftype.size and
                            not isinstance(ftype, W_CTypePrimitiveChar)):
            fbitsize = -1
            bitshift = -1
            prev_bit_position = 0
        else:
            xxx
        #
        fld = ctypeobj.W_CField(ftype, offset, bitshift, fbitsize)
        fields_list.append(fld)
        fields_dict[fname] = fld
        #
        if maxsize < ftype.size:
            maxsize = ftype.size
        if not is_union:
            offset += ftype.size

    if is_union:
        assert offset == 0
        offset = maxsize
    else:
        if offset == 0:
            offset = 1
        offset = (offset + alignment - 1) & ~(alignment-1)

    if totalsize < 0:
        totalsize = offset
    elif totalsize < offset:
        raise operationerrfmt(space.w_TypeError,
                     "%s cannot be of size %d: there are fields at least "
                     "up to %d", ctype.name, totalsize, offset)
    if totalalignment < 0:
        totalalignment = alignment

    ctype.size = totalsize
    ctype.alignment = totalalignment
    ctype.fields_list = fields_list
    ctype.fields_dict = fields_dict
