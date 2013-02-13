from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import unwrap_spec
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import ovfcheck, r_uint, intmask
from rpython.rlib.rarithmetic import most_neg_value_of, most_pos_value_of
from rpython.rlib.objectmodel import specialize

from pypy.module._cffi_backend import ctypeobj, ctypeprim, ctypeptr, ctypearray
from pypy.module._cffi_backend import ctypestruct, ctypevoid, ctypeenum


@specialize.memo()
def alignment(TYPE):
    S = lltype.Struct('aligncheck', ('x', lltype.Char), ('y', TYPE))
    return rffi.offsetof(S, 'y')

alignment_of_pointer = alignment(rffi.CCHARP)

# ____________________________________________________________


PRIMITIVE_TYPES = {}

def eptype(name, TYPE, ctypecls):
    PRIMITIVE_TYPES[name] = ctypecls, rffi.sizeof(TYPE), alignment(TYPE)

def eptypesize(name, size, ctypecls):
    for TYPE in [lltype.Signed, lltype.SignedLongLong, rffi.SIGNEDCHAR,
                 rffi.SHORT, rffi.INT, rffi.LONG, rffi.LONGLONG]:
        if rffi.sizeof(TYPE) == size:
            eptype(name, TYPE, ctypecls)
            return
    raise NotImplementedError("no integer type of size %d??" % size)

eptype("char",        lltype.Char,     ctypeprim.W_CTypePrimitiveChar)
eptype("wchar_t",     lltype.UniChar,  ctypeprim.W_CTypePrimitiveUniChar)
eptype("signed char", rffi.SIGNEDCHAR, ctypeprim.W_CTypePrimitiveSigned)
eptype("short",       rffi.SHORT,      ctypeprim.W_CTypePrimitiveSigned)
eptype("int",         rffi.INT,        ctypeprim.W_CTypePrimitiveSigned)
eptype("long",        rffi.LONG,       ctypeprim.W_CTypePrimitiveSigned)
eptype("long long",   rffi.LONGLONG,   ctypeprim.W_CTypePrimitiveSigned)
eptype("unsigned char",      rffi.UCHAR,    ctypeprim.W_CTypePrimitiveUnsigned)
eptype("unsigned short",     rffi.SHORT,    ctypeprim.W_CTypePrimitiveUnsigned)
eptype("unsigned int",       rffi.INT,      ctypeprim.W_CTypePrimitiveUnsigned)
eptype("unsigned long",      rffi.LONG,     ctypeprim.W_CTypePrimitiveUnsigned)
eptype("unsigned long long", rffi.LONGLONG, ctypeprim.W_CTypePrimitiveUnsigned)
eptype("float",  rffi.FLOAT,  ctypeprim.W_CTypePrimitiveFloat)
eptype("double", rffi.DOUBLE, ctypeprim.W_CTypePrimitiveFloat)
eptype("long double", rffi.LONGDOUBLE, ctypeprim.W_CTypePrimitiveLongDouble)
eptype("_Bool",  lltype.Bool,          ctypeprim.W_CTypePrimitiveBool)

eptypesize("int8_t",   1, ctypeprim.W_CTypePrimitiveSigned)
eptypesize("uint8_t",  1, ctypeprim.W_CTypePrimitiveUnsigned)
eptypesize("int16_t",  2, ctypeprim.W_CTypePrimitiveSigned)
eptypesize("uint16_t", 2, ctypeprim.W_CTypePrimitiveUnsigned)
eptypesize("int32_t",  4, ctypeprim.W_CTypePrimitiveSigned)
eptypesize("uint32_t", 4, ctypeprim.W_CTypePrimitiveUnsigned)
eptypesize("int64_t",  8, ctypeprim.W_CTypePrimitiveSigned)
eptypesize("uint64_t", 8, ctypeprim.W_CTypePrimitiveUnsigned)

eptype("intptr_t",  rffi.INTPTR_T,  ctypeprim.W_CTypePrimitiveSigned)
eptype("uintptr_t", rffi.UINTPTR_T, ctypeprim.W_CTypePrimitiveUnsigned)
eptype("ptrdiff_t", rffi.INTPTR_T,  ctypeprim.W_CTypePrimitiveSigned) # <-xxx
eptype("size_t",    rffi.SIZE_T,    ctypeprim.W_CTypePrimitiveUnsigned)
eptype("ssize_t",   rffi.SSIZE_T,   ctypeprim.W_CTypePrimitiveSigned)

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
    ctypepointer = ctypeptr.W_CTypePointer(space, ctype)
    return ctypepointer

# ____________________________________________________________

@unwrap_spec(ctptr=ctypeobj.W_CType)
def new_array_type(space, ctptr, w_length):
    if not isinstance(ctptr, ctypeptr.W_CTypePointer):
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
    ctype = ctypearray.W_CTypeArray(space, ctptr, length, arraysize, extra)
    return ctype

# ____________________________________________________________

@unwrap_spec(name=str)
def new_struct_type(space, name):
    return ctypestruct.W_CTypeStruct(space, name)

@unwrap_spec(name=str)
def new_union_type(space, name):
    return ctypestruct.W_CTypeUnion(space, name)

@unwrap_spec(ctype=ctypeobj.W_CType, totalsize=int, totalalignment=int)
def complete_struct_or_union(space, ctype, w_fields, w_ignored=None,
                             totalsize=-1, totalalignment=-1):
    if (not isinstance(ctype, ctypestruct.W_CTypeStructOrUnion)
            or ctype.size >= 0):
        raise OperationError(space.w_TypeError,
                             space.wrap("first arg must be a non-initialized"
                                        " struct or union ctype"))

    is_union = isinstance(ctype, ctypestruct.W_CTypeUnion)
    maxsize = 1
    alignment = 1
    offset = 0
    fields_w = space.listview(w_fields)
    fields_list = []
    fields_dict = {}
    prev_bit_position = 0
    custom_field_pos = False

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
            # a forced field position: ignore the offset just computed,
            # except to know if we must set 'custom_field_pos'
            custom_field_pos |= (offset != foffset)
            offset = foffset
        #
        if fbitsize < 0 or (
                fbitsize == 8 * ftype.size and not
                isinstance(ftype, ctypeprim.W_CTypePrimitiveCharOrUniChar)):
            fbitsize = -1
            if isinstance(ftype, ctypearray.W_CTypeArray) and ftype.length==0:
                bitshift = ctypestruct.W_CField.BS_EMPTY_ARRAY
            else:
                bitshift = ctypestruct.W_CField.BS_REGULAR
            prev_bit_position = 0
        else:
            if (not (isinstance(ftype, ctypeprim.W_CTypePrimitiveSigned) or
                     isinstance(ftype, ctypeprim.W_CTypePrimitiveUnsigned) or
                     isinstance(ftype, ctypeprim.W_CTypePrimitiveChar)) or
                fbitsize == 0 or
                fbitsize > 8 * ftype.size):
                raise operationerrfmt(space.w_TypeError,
                                      "invalid bit field '%s'", fname)
            if prev_bit_position > 0:
                prev_field = fields_list[-1]
                assert prev_field.bitshift >= 0
                if prev_field.ctype.size != ftype.size:
                    raise OperationError(space.w_NotImplementedError,
                        space.wrap("consecutive bit fields should be "
                                   "declared with a same-sized type"))
                if prev_bit_position + fbitsize > 8 * ftype.size:
                    prev_bit_position = 0
                else:
                    # we can share the same field as 'prev_field'
                    offset = prev_field.offset
            bitshift = prev_bit_position
            if not is_union:
                prev_bit_position += fbitsize
        #
        if (len(fname) == 0 and
            isinstance(ftype, ctypestruct.W_CTypeStructOrUnion)):
            # a nested anonymous struct or union
            srcfield2names = {}
            for name, srcfld in ftype.fields_dict.items():
                srcfield2names[srcfld] = name
            for srcfld in ftype.fields_list:
                fld = srcfld.make_shifted(offset)
                fields_list.append(fld)
                try:
                    fields_dict[srcfield2names[srcfld]] = fld
                except KeyError:
                    pass
            # always forbid such structures from being passed by value
            custom_field_pos = True
        else:
            # a regular field
            fld = ctypestruct.W_CField(ftype, offset, bitshift, fbitsize)
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

    # Like C, if the size of this structure would be zero, we compute it
    # as 1 instead.  But for ctypes support, we allow the manually-
    # specified totalsize to be zero in this case.
    if totalsize < 0:
        offset = (offset + alignment - 1) & ~(alignment-1)
        totalsize = offset or 1
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
    ctype.custom_field_pos = custom_field_pos

# ____________________________________________________________

def new_void_type(space):
    ctype = ctypevoid.W_CTypeVoid(space)
    return ctype

# ____________________________________________________________

@unwrap_spec(name=str)
def new_enum_type(space, name, w_enumerators, w_enumvalues):
    enumerators_w = space.fixedview(w_enumerators)
    enumvalues_w  = space.fixedview(w_enumvalues)
    if len(enumerators_w) != len(enumvalues_w):
        raise OperationError(space.w_ValueError,
                             space.wrap("tuple args must have the same size"))
    enumerators = [space.str_w(w) for w in enumerators_w]
    #
    smallest_value = 0
    largest_value = r_uint(0)
    i = 0
    try:
        for w in enumvalues_w:
            try:
                ulvalue = space.uint_w(w)
            except OperationError, e:
                if not e.match(space, space.w_ValueError):
                    raise
                lvalue = space.int_w(w)
                if lvalue < smallest_value:
                    smallest_value = lvalue
            else:
                if ulvalue > largest_value:
                    largest_value = ulvalue
            i += 1    # 'i' is here for the exception case, see below
    except OperationError, e:
        if not e.match(space, space.w_OverflowError):
            raise
        raise operationerrfmt(space.w_OverflowError,
                              "enum '%s' declaration for '%s' does not fit "
                              "a long or unsigned long",
                              name, enumerators[i])
    #
    if smallest_value < 0:
        if (smallest_value >= intmask(most_neg_value_of(rffi.INT)) and
             largest_value <= r_uint(most_pos_value_of(rffi.INT))):
            size = rffi.sizeof(rffi.INT)
            align = alignment(rffi.INT)
        elif largest_value <= r_uint(most_pos_value_of(rffi.LONG)):
            size = rffi.sizeof(rffi.LONG)
            align = alignment(rffi.LONG)
        else:
            raise operationerrfmt(space.w_OverflowError,
                         "enum '%s' values don't all fit into either 'long' "
                         "or 'unsigned long'", name)
        enumvalues = [space.int_w(w) for w in enumvalues_w]
        ctype = ctypeenum.W_CTypeEnumSigned(space, name, size, align,
                                            enumerators, enumvalues)
    else:
        if largest_value <= r_uint(most_pos_value_of(rffi.UINT)):
            size = rffi.sizeof(rffi.UINT)
            align = alignment(rffi.UINT)
        else:
            size = rffi.sizeof(rffi.ULONG)
            align = alignment(rffi.ULONG)
        enumvalues = [space.uint_w(w) for w in enumvalues_w]
        ctype = ctypeenum.W_CTypeEnumUnsigned(space, name, size, align,
                                              enumerators, enumvalues)
    return ctype

# ____________________________________________________________

@unwrap_spec(fresult=ctypeobj.W_CType, ellipsis=int)
def new_function_type(space, w_fargs, fresult, ellipsis=0):
    from pypy.module._cffi_backend import ctypefunc
    fargs = []
    for w_farg in space.fixedview(w_fargs):
        farg = space.interpclass_w(w_farg)
        if not isinstance(farg, ctypeobj.W_CType):
            raise OperationError(space.w_TypeError,
                space.wrap("first arg must be a tuple of ctype objects"))
        if isinstance(farg, ctypearray.W_CTypeArray):
            farg = farg.ctptr
        fargs.append(farg)
    #
    if ((fresult.size < 0 and not isinstance(fresult, ctypevoid.W_CTypeVoid))
            or isinstance(fresult, ctypearray.W_CTypeArray)):
        raise operationerrfmt(space.w_TypeError,
                              "invalid result type: '%s'", fresult.name)
    #
    fct = ctypefunc.W_CTypeFunc(space, fargs, fresult, ellipsis)
    return fct
