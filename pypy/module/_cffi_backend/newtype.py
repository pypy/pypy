import sys
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import unwrap_spec

from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import ovfcheck
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform

from pypy.module._cffi_backend import (ctypeobj, ctypeprim, ctypeptr,
    ctypearray, ctypestruct, ctypevoid, ctypeenum)


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

@unwrap_spec(w_ctype=ctypeobj.W_CType)
def new_pointer_type(space, w_ctype):
    ctypepointer = ctypeptr.W_CTypePointer(space, w_ctype)
    return ctypepointer

# ____________________________________________________________

@unwrap_spec(w_ctptr=ctypeobj.W_CType)
def new_array_type(space, w_ctptr, w_length):
    if not isinstance(w_ctptr, ctypeptr.W_CTypePointer):
        raise OperationError(space.w_TypeError,
                             space.wrap("first arg must be a pointer ctype"))
    ctitem = w_ctptr.ctitem
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
    ctype = ctypearray.W_CTypeArray(space, w_ctptr, length, arraysize, extra)
    return ctype

# ____________________________________________________________

SF_MSVC_BITFIELDS = 1
SF_GCC_ARM_BITFIELDS = 2
SF_GCC_BIG_ENDIAN = 4
SF_PACKED = 8

if sys.platform == 'win32':
    DEFAULT_SFLAGS = SF_MSVC_BITFIELDS
else:
    if rffi_platform.getdefined('__arm__', ''):
        DEFAULT_SFLAGS = SF_GCC_ARM_BITFIELDS
    else:
        DEFAULT_SFLAGS = 0
    if sys.byteorder == 'big':
        DEFAULT_SFLAGS |= SF_GCC_BIG_ENDIAN

@unwrap_spec(name=str)
def new_struct_type(space, name):
    return ctypestruct.W_CTypeStruct(space, name)

@unwrap_spec(name=str)
def new_union_type(space, name):
    return ctypestruct.W_CTypeUnion(space, name)

@unwrap_spec(w_ctype=ctypeobj.W_CType, totalsize=int, totalalignment=int,
             sflags=int)
def complete_struct_or_union(space, w_ctype, w_fields, w_ignored=None,
                             totalsize=-1, totalalignment=-1,
                             sflags=DEFAULT_SFLAGS):
    if (not isinstance(w_ctype, ctypestruct.W_CTypeStructOrUnion)
            or w_ctype.size >= 0):
        raise OperationError(space.w_TypeError,
                             space.wrap("first arg must be a non-initialized"
                                        " struct or union ctype"))

    is_union = isinstance(w_ctype, ctypestruct.W_CTypeUnion)
    alignment = 1
    boffset = 0         # this number is in *bits*, not bytes!
    boffsetmax = 0      # the maximum value of boffset, in bits too
    prev_bitfield_size = 0
    prev_bitfield_free = 0
    fields_w = space.listview(w_fields)
    fields_list = []
    fields_dict = {}
    custom_field_pos = False
    with_var_array = False

    for i in range(len(fields_w)):
        w_field = fields_w[i]
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
            if (isinstance(ftype, ctypearray.W_CTypeArray) and fbitsize < 0
                    and (i == len(fields_w) - 1 or foffset != -1)):
                with_var_array = True
            else:
                raise operationerrfmt(space.w_TypeError,
                    "field '%s.%s' has ctype '%s' of unknown size",
                                  w_ctype.name, fname, ftype.name)
        #
        if is_union:
            boffset = 0         # reset each field at offset 0
        #
        # update the total alignment requirement, but skip it if the
        # field is an anonymous bitfield or if SF_PACKED
        falign = 1 if sflags & SF_PACKED else ftype.alignof()
        do_align = True
        if (sflags & SF_GCC_ARM_BITFIELDS) == 0 and fbitsize >= 0:
            if (sflags & SF_MSVC_BITFIELDS) == 0:
                # GCC: anonymous bitfields (of any size) don't cause alignment
                do_align = (fname != '')
            else:
                # MSVC: zero-sized bitfields don't cause alignment
                do_align = (fbitsize > 0)
        if alignment < falign and do_align:
            alignment = falign
        #
        if fbitsize < 0:
            # not a bitfield: common case

            if isinstance(ftype, ctypearray.W_CTypeArray) and ftype.length==0:
                bs_flag = ctypestruct.W_CField.BS_EMPTY_ARRAY
            else:
                bs_flag = ctypestruct.W_CField.BS_REGULAR

            # align this field to its own 'falign' by inserting padding
            boffset = (boffset + falign*8-1) & ~(falign*8-1)

            if foffset >= 0:
                # a forced field position: ignore the offset just computed,
                # except to know if we must set 'custom_field_pos'
                custom_field_pos |= (boffset != foffset * 8)
                boffset = foffset * 8

            if (fname == '' and
                    isinstance(ftype, ctypestruct.W_CTypeStructOrUnion)):
                # a nested anonymous struct or union
                srcfield2names = {}
                for name, srcfld in ftype.fields_dict.items():
                    srcfield2names[srcfld] = name
                for srcfld in ftype.fields_list:
                    fld = srcfld.make_shifted(boffset // 8)
                    fields_list.append(fld)
                    try:
                        fields_dict[srcfield2names[srcfld]] = fld
                    except KeyError:
                        pass
                # always forbid such structures from being passed by value
                custom_field_pos = True
            else:
                # a regular field
                fld = ctypestruct.W_CField(ftype, boffset // 8, bs_flag, -1)
                fields_list.append(fld)
                fields_dict[fname] = fld

            if ftype.size >= 0:
                boffset += ftype.size * 8
            prev_bitfield_size = 0

        else:
            # this is the case of a bitfield

            if foffset >= 0:
                raise operationerrfmt(space.w_TypeError,
                                      "field '%s.%s' is a bitfield, "
                                      "but a fixed offset is specified",
                                      w_ctype.name, fname)

            if not (isinstance(ftype, ctypeprim.W_CTypePrimitiveSigned) or
                    isinstance(ftype, ctypeprim.W_CTypePrimitiveUnsigned) or
                    isinstance(ftype,ctypeprim.W_CTypePrimitiveCharOrUniChar)):
                raise operationerrfmt(space.w_TypeError,
                                      "field '%s.%s' declared as '%s' "
                                      "cannot be a bit field",
                                      w_ctype.name, fname, ftype.name)
            if fbitsize > 8 * ftype.size:
                raise operationerrfmt(space.w_TypeError,
                                      "bit field '%s.%s' is declared '%s:%d',"
                                      " which exceeds the width of the type",
                                      w_ctype.name, fname,
                                      ftype.name, fbitsize)

            # compute the starting position of the theoretical field
            # that covers a complete 'ftype', inside of which we will
            # locate the real bitfield
            field_offset_bytes = boffset // 8
            field_offset_bytes &= ~(falign - 1)

            if fbitsize == 0:
                if fname != '':
                    raise operationerrfmt(space.w_TypeError,
                                          "field '%s.%s' is declared with :0",
                                          w_ctype.name, fname)
                if (sflags & SF_MSVC_BITFIELDS) == 0:
                    # GCC's notion of "ftype :0;"
                    # pad boffset to a value aligned for "ftype"
                    if boffset > field_offset_bytes * 8:
                        field_offset_bytes += falign
                        assert boffset < field_offset_bytes * 8
                    boffset = field_offset_bytes * 8
                else:
                    # MSVC's notion of "ftype :0;
                    # Mostly ignored.  It seems they only serve as
                    # separator between other bitfields, to force them
                    # into separate words.
                    pass
                prev_bitfield_size = 0

            else:
                if (sflags & SF_MSVC_BITFIELDS) == 0:
                    # GCC's algorithm

                    # Can the field start at the offset given by 'boffset'?  It
                    # can if it would entirely fit into an aligned ftype field.
                    bits_already_occupied = boffset - (field_offset_bytes * 8)

                    if bits_already_occupied + fbitsize > 8 * ftype.size:
                        # it would not fit, we need to start at the next
                        # allowed position
                        if ((sflags & SF_PACKED) != 0 and
                            (bits_already_occupied & 7) != 0):
                            raise operationerrfmt(space.w_NotImplementedError,
                                "with 'packed', gcc would compile field "
                                "'%s.%s' to reuse some bits in the previous "
                                "field", w_ctype.name, fname)
                        field_offset_bytes += falign
                        assert boffset < field_offset_bytes * 8
                        boffset = field_offset_bytes * 8
                        bitshift = 0
                    else:
                        bitshift = bits_already_occupied
                        assert bitshift >= 0
                    boffset += fbitsize

                else:
                    # MSVC's algorithm

                    # A bitfield is considered as taking the full width
                    # of their declared type.  It can share some bits
                    # with the previous field only if it was also a
                    # bitfield and used a type of the same size.
                    if (prev_bitfield_size == ftype.size and
                        prev_bitfield_free >= fbitsize):
                        # yes: reuse
                        bitshift = 8 * prev_bitfield_size - prev_bitfield_free
                    else:
                        # no: start a new full field
                        boffset = (boffset + falign*8-1) & ~(falign*8-1)
                        boffset += ftype.size * 8
                        bitshift = 0
                        prev_bitfield_size = ftype.size
                        prev_bitfield_free = 8 * prev_bitfield_size
                    #
                    prev_bitfield_free -= fbitsize
                    field_offset_bytes = boffset / 8 - ftype.size

                if sflags & SF_GCC_BIG_ENDIAN:
                    bitshift = 8 * ftype.size - fbitsize- bitshift

                fld = ctypestruct.W_CField(ftype, field_offset_bytes,
                                           bitshift, fbitsize)
                fields_list.append(fld)
                fields_dict[fname] = fld

        if boffset > boffsetmax:
            boffsetmax = boffset

    # Like C, if the size of this structure would be zero, we compute it
    # as 1 instead.  But for ctypes support, we allow the manually-
    # specified totalsize to be zero in this case.
    got = (boffsetmax + 7) // 8
    if totalsize < 0:
        totalsize = (got + alignment - 1) & ~(alignment - 1)
        totalsize = totalsize or 1
    elif totalsize < got:
        raise operationerrfmt(space.w_TypeError,
                     "%s cannot be of size %d: there are fields at least "
                     "up to %d", w_ctype.name, totalsize, got)
    if totalalignment < 0:
        totalalignment = alignment

    w_ctype.size = totalsize
    w_ctype.alignment = totalalignment
    w_ctype.fields_list = fields_list
    w_ctype.fields_dict = fields_dict
    w_ctype.custom_field_pos = custom_field_pos
    w_ctype.with_var_array = with_var_array

# ____________________________________________________________

def new_void_type(space):
    ctype = ctypevoid.W_CTypeVoid(space)
    return ctype

# ____________________________________________________________

@unwrap_spec(name=str, w_basectype=ctypeobj.W_CType)
def new_enum_type(space, name, w_enumerators, w_enumvalues, w_basectype):
    enumerators_w = space.fixedview(w_enumerators)
    enumvalues_w  = space.fixedview(w_enumvalues)
    if len(enumerators_w) != len(enumvalues_w):
        raise OperationError(space.w_ValueError,
                             space.wrap("tuple args must have the same size"))
    enumerators = [space.str_w(w) for w in enumerators_w]
    #
    if (not isinstance(w_basectype, ctypeprim.W_CTypePrimitiveSigned) and
        not isinstance(w_basectype, ctypeprim.W_CTypePrimitiveUnsigned)):
        raise OperationError(space.w_TypeError,
              space.wrap("expected a primitive signed or unsigned base type"))
    #
    lvalue = lltype.malloc(rffi.CCHARP.TO, w_basectype.size, flavor='raw')
    try:
        for w in enumvalues_w:
            # detects out-of-range or badly typed values
            w_basectype.convert_from_object(lvalue, w)
    finally:
        lltype.free(lvalue, flavor='raw')
    #
    size = w_basectype.size
    align = w_basectype.align
    if isinstance(w_basectype, ctypeprim.W_CTypePrimitiveSigned):
        enumvalues = [space.int_w(w) for w in enumvalues_w]
        ctype = ctypeenum.W_CTypeEnumSigned(space, name, size, align,
                                            enumerators, enumvalues)
    else:
        enumvalues = [space.uint_w(w) for w in enumvalues_w]
        ctype = ctypeenum.W_CTypeEnumUnsigned(space, name, size, align,
                                              enumerators, enumvalues)
    return ctype

# ____________________________________________________________

@unwrap_spec(w_fresult=ctypeobj.W_CType, ellipsis=int)
def new_function_type(space, w_fargs, w_fresult, ellipsis=0):
    from pypy.module._cffi_backend import ctypefunc
    fargs = []
    for w_farg in space.fixedview(w_fargs):
        if not isinstance(w_farg, ctypeobj.W_CType):
            raise OperationError(space.w_TypeError,
                space.wrap("first arg must be a tuple of ctype objects"))
        if isinstance(w_farg, ctypearray.W_CTypeArray):
            w_farg = w_farg.ctptr
        fargs.append(w_farg)
    #
    if ((w_fresult.size < 0 and
         not isinstance(w_fresult, ctypevoid.W_CTypeVoid))
        or isinstance(w_fresult, ctypearray.W_CTypeArray)):
        if (isinstance(w_fresult, ctypestruct.W_CTypeStructOrUnion) and
                w_fresult.size < 0):
            raise operationerrfmt(space.w_TypeError,
                                  "result type '%s' is opaque", w_fresult.name)
        else:
            raise operationerrfmt(space.w_TypeError,
                                  "invalid result type: '%s'", w_fresult.name)
    #
    fct = ctypefunc.W_CTypeFunc(space, fargs, w_fresult, ellipsis)
    return fct
