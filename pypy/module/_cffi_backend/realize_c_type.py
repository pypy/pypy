import sys
from rpython.rlib.rarithmetic import intmask
from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.interpreter.error import oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.module._cffi_backend.ctypeobj import W_CType
from pypy.module._cffi_backend import cffi_opcode, newtype, ctypestruct
from pypy.module._cffi_backend import parse_c_type


def getop(op):
    return rffi.cast(rffi.SIGNED, op) & 0xFF

def getarg(op):
    return rffi.cast(rffi.SIGNED, op) >> 8



class RealizeCache:
    NAMES = [None,
        "_Bool",
        "char",
        "signed char",
        "unsigned char",
        "short",
        "unsigned short",
        "int",
        "unsigned int",
        "long",
        "unsigned long",
        "long long",
        "unsigned long long",
        "float",
        "double",
        "long double",
        "wchar_t",
        "int8_t",
        "uint8_t",
        "int16_t",
        "uint16_t",
        "int32_t",
        "uint32_t",
        "int64_t",
        "uint64_t",
        "intptr_t",
        "uintptr_t",
        "ptrdiff_t",
        "size_t",
        "ssize_t",
        "int_least8_t",
        "uint_least8_t",
        "int_least16_t",
        "uint_least16_t",
        "int_least32_t",
        "uint_least32_t",
        "int_least64_t",
        "uint_least64_t",
        "int_fast8_t",
        "uint_fast8_t",
        "int_fast16_t",
        "uint_fast16_t",
        "int_fast32_t",
        "uint_fast32_t",
        "int_fast64_t",
        "uint_fast64_t",
        "intmax_t",
        "uintmax_t",
        ]
    def __init__(self, space):
        self.all_primitives = [None] * cffi_opcode._NUM_PRIM

def get_primitive_type(space, num):
    realize_cache = space.fromcache(RealizeCache)
    w_ctype = realize_cache.all_primitives[num]
    if w_ctype is None:
        if num == cffi_opcode.PRIM_VOID:
            w_ctype = newtype.new_void_type(space)
        elif 0 <= num < len(RealizeCache.NAMES) and RealizeCache.NAMES[num]:
            w_ctype = newtype.new_primitive_type(space, RealizeCache.NAMES[num])
        else:
            raise oefmt(ffi.space.w_NotImplementedError, "prim=%d", case)
        realize_cache.all_primitives[num] = w_ctype
    return w_ctype

def get_array_type(ffi, opcodes, itemindex, length):
    w_ctitem = realize_c_type(ffi, opcodes, itemindex)
    w_ctitemptr = newtype.new_pointer_type(ffi.space, w_ctitem)
    return newtype._new_array_type(ffi.space, w_ctitemptr, length)


FUNCPTR_FETCH_CHARP = lltype.Ptr(lltype.FuncType([rffi.CCHARP], lltype.Void))
FUNCPTR_FETCH_LONGLONG = lltype.Ptr(lltype.FuncType([rffi.ULONGLONGP],
                                                    rffi.INT))
def realize_global_int(ffi, g):
    fetch_fnptr = rffi.cast(FUNCPTR_FETCH_LONGLONG, g.c_address)
    with lltype.scoped_alloc(rffi.ULONGLONGP.TO, 1) as p_value:
        neg = fetch_fnptr(p_value)
        value = p_value[0]
    neg = rffi.cast(lltype.Signed, neg)

    if neg == 0:     # positive
        if value <= sys.maxint:
            return ffi.space.wrap(intmask(value))
        else:
            return ffi.space.wrap(value)
    elif neg == 1:   # negative
        if value >= -sys.maxint-1:
            return ffi.space.wrap(intmask(value))
        else:
            return ffi.space.wrap(rffi.cast(rffi.LONGLONG, value))

    if neg == 2:
        got = "%d (0x%x)" % (value, value)
    else:
        got = "%d" % (rffi.cast(rffi.LONGLONG, value),)
    raise oefmt(ffi.w_FFIError,
                "the C compiler says '%s' is equal to %s, "
                "but the cdef disagrees", rffi.charp2str(g.c_name), got)


class W_RawFuncType(W_Root):
    """Temporary: represents a C function type (not a function pointer)"""
    def __init__(self, w_ctfuncptr):
        self.w_ctfuncptr = w_ctfuncptr

def unwrap_fn_as_fnptr(x):
    assert isinstance(x, W_RawFuncType)
    return x.w_ctfuncptr

def unexpected_fn_type(ffi, x):
    x = unwrap_fn_as_fnptr(x)
    # here, x.name is for example 'int(*)(int)'
    #                                   ^
    j = x.name_position - 2
    assert j >= 0
    text1 = x.name[:j]
    text2 = x.name[x.name_position+1:]
    raise oefmt(ffi.w_FFIError, "the type '%s%s' is a function type, not a "
                                "pointer-to-function type", text1, text2)


def realize_c_type(ffi, opcodes, index):
    """Interpret an opcodes[] array.  If opcodes == ffi.ctxobj.ctx.c_types,
    store all the intermediate types back in the opcodes[].
    """
    x = realize_c_type_or_func(ffi, opcodes, index)
    if not isinstance(x, W_CType):
        unexpected_fn_type(ffi, x)
    return x


def _realize_name(prefix, charp_src_name):
    # "xyz" => "struct xyz"
    #"$xyz" => "xyz"
    if charp_src_name[0] == '$' and charp_src_name[1] != '$':
        return rffi.charp2str(rffi.ptradd(charp_src_name, 1))
    else:
        return prefix + rffi.charp2str(charp_src_name)


def _realize_c_struct_or_union(ffi, sindex):
    s = ffi.ctxobj.ctx.c_struct_unions[sindex]
    type_index = rffi.getintfield(s, 'c_type_index')
    if ffi.cached_types[type_index] is not None:
        return ffi.cached_types[type_index] #found already in the "primary" slot

    w_ctype = None
    c_flags = rffi.getintfield(s, 'c_flags')
    if (c_flags & cffi_opcode.F_EXTERNAL) == 0:
        space = ffi.space
        if (c_flags & cffi_opcode.F_UNION) != 0:
            name = _realize_name("union ", s.c_name)
            x = ctypestruct.W_CTypeUnion(space, name)
        else:
            name = _realize_name("struct ", s.c_name)
            x = ctypestruct.W_CTypeStruct(space, name)
        if rffi.getintfield(s, 'c_first_field_index') >= 0:
            w_ctype = x
            w_ctype.size = rffi.getintfield(s, 'c_size')
            w_ctype.alignment = rffi.getintfield(s, 'c_alignment')
            # w_ctype._field_list and other underscore fields are still
            # None, making it a "lazy" (i.e. "non-forced") kind of struct
            w_ctype._lazy_ffi = ffi
            w_ctype._lazy_s = s
    else:
        yyyy

    # Update the "primary" OP_STRUCT_UNION slot
    ffi.cached_types[type_index] = x

    if w_ctype is not None and rffi.getintfield(s, 'c_size') == -2:
        # oops, this struct is unnamed and we couldn't generate
        # a C expression to get its size.  We have to rely on
        # complete_struct_or_union() to compute it now.
        try:
            do_realize_lazy_struct(ffi, w_ctype)
        except:
            ffi.cached_types[type_index] = None
            raise
    return x


def realize_c_type_or_func(ffi, opcodes, index):
    op = opcodes[index]

    from_ffi = (opcodes == ffi.ctxobj.ctx.c_types)
    if from_ffi and ffi.cached_types[index] is not None:
        return ffi.cached_types[index]

    case = getop(op)

    if case == cffi_opcode.OP_PRIMITIVE:
        x = get_primitive_type(ffi.space, getarg(op))

    elif case == cffi_opcode.OP_POINTER:
        y = realize_c_type_or_func(ffi, opcodes, getarg(op))
        if isinstance(y, W_CType):
            x = newtype.new_pointer_type(ffi.space, y)
        elif isinstance(y, W_RawFuncType):
            x = y.w_ctfuncptr
        else:
            raise NotImplementedError

    elif case == cffi_opcode.OP_ARRAY:
        x = get_array_type(ffi, opcodes, getarg(op),
                           rffi.cast(rffi.SIGNED, opcodes[index + 1]))

    elif case == cffi_opcode.OP_OPEN_ARRAY:
        x = get_array_type(ffi, opcodes, getarg(op), -1)

    elif case == cffi_opcode.OP_STRUCT_UNION:
        x = _realize_c_struct_or_union(ffi, getarg(op))

    elif case == cffi_opcode.OP_FUNCTION:
        y = realize_c_type(ffi, opcodes, getarg(op))
        base_index = index + 1
        num_args = 0
        OP_FUNCTION_END = cffi_opcode.OP_FUNCTION_END
        while getop(opcodes[base_index + num_args]) != OP_FUNCTION_END:
            num_args += 1
        ellipsis = (getarg(opcodes[base_index + num_args]) & 1) != 0
        fargs = [realize_c_type(ffi, opcodes, base_index + i)
                 for i in range(num_args)]
        w_ctfuncptr = newtype._new_function_type(ffi.space, fargs, y, ellipsis)
        x = W_RawFuncType(w_ctfuncptr)

    elif case == cffi_opcode.OP_NOOP:
        x = realize_c_type_or_func(ffi, opcodes, getarg(op))

    elif case == cffi_opcode.OP_TYPENAME:
        # essential: the TYPENAME opcode resolves the type index looked
        # up in the 'ctx.c_typenames' array, but it does so in 'ctx.c_types'
        # instead of in 'opcodes'!
        type_index = rffi.getintfield(ffi.ctxobj.ctx.c_typenames[getarg(op)],
                                      'c_type_index')
        x = realize_c_type_or_func(ffi, ffi.ctxobj.ctx.c_types, type_index)

    else:
        raise oefmt(ffi.space.w_NotImplementedError, "op=%d", case)

    if from_ffi:
        assert ffi.cached_types[index] is None or ffi.cached_types[index] is x
        ffi.cached_types[index] = x

    return x


def do_realize_lazy_struct(w_ctype):
    """This is called by W_CTypeStructOrUnion.force_lazy_struct().
    """
    assert isinstance(w_ctype, ctypestruct.W_CTypeStructOrUnion)
    space = w_ctype.space
    ffi = w_ctype._lazy_ffi
    s = w_ctype._lazy_s
    assert w_ctype.size != -1      # not an opaque
    assert ffi is not None         # still lazy

    first_field = rffi.getintfield(s, 'c_first_field_index')
    num_fields = rffi.getintfield(s, 'c_num_fields')
    fields_w = [None] * num_fields

    for i in range(num_fields):
        fbitsize = -1
        fld = ffi.ctxobj.ctx.c_fields[first_field + i]
        op = rffi.getintfield(fld, 'c_field_type_op')
        case = getop(op)

        if case == cffi_opcode.OP_NOOP:
            # standard field
            w_ctf = realize_c_type(ffi, ffi.ctxobj.ctx.c_types, getarg(op))
        else:
            raise oefmt(space.w_NotImplementedError, "field op=%d", case)

        field_name   = rffi.charp2str(fld.c_name)
        field_size   = rffi.getintfield(fld, 'c_field_size')
        field_offset = rffi.getintfield(fld, 'c_field_offset')
        if field_offset == -1:
            xxxx
        else:
            newtype.detect_custom_layout(w_ctype, newtype.SF_STD_FIELD_POS,
                                         w_ctf.size, field_size,
                                         "wrong size for field '",
                                         field_name, "'")

        fields_w[i] = space.newtuple([
            space.wrap(field_name),
            w_ctf,
            space.wrap(fbitsize),
            space.wrap(field_offset)])

    sflags = 0
    c_flags = rffi.getintfield(s, 'c_flags')
    if c_flags & cffi_opcode.F_CHECK_FIELDS:
        sflags |= newtype.SF_STD_FIELD_POS
    if c_flags & cffi_opcode.F_PACKED:
        sflags |= newtype.SF_PACKED

    assert w_ctype.size      == rffi.getintfield(s, 'c_size')
    assert w_ctype.alignment == rffi.getintfield(s, 'c_alignment')
    try:
        w_ctype.size = -1              # make opaque again
        newtype.complete_struct_or_union(
            space, w_ctype, space.newlist(fields_w), space.w_None,
            totalsize = rffi.getintfield(s, 'c_size'),
            totalalignment = rffi.getintfield(s, 'c_alignment'),
            sflags = sflags)
    except:
        w_ctype.size      = rffi.getintfield(s, 'c_size')       # restore
        w_ctype.alignment = rffi.getintfield(s, 'c_alignment')  # restore
        raise
    assert w_ctype.size      == rffi.getintfield(s, 'c_size')
    assert w_ctype.alignment == rffi.getintfield(s, 'c_alignment')
    assert w_ctype._fields_list is not None       # not lazy any more

    w_ctype._lazy_ffi = None
    w_ctype._lazy_s = lltype.nullptr(parse_c_type.FIELD_S)
