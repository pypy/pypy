from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import oefmt
from pypy.module._cffi_backend import cdataobj, ctypeptr, ctypeprim, misc
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import intmask


@specialize.memo()
def get_unsafe_type_ptr(TP):
    UNSAFE = lltype.Array(TP, hints={'nolength': True,
                                     'stm_dont_track_raw_accesses': True})
    return lltype.Ptr(UNSAFE)


def unsafe_write_raw_signed_data(w_cdata, index, source, size):
    with w_cdata as target:
        for TP, _ in misc._prim_signed_types:
            if size == rffi.sizeof(TP):
                TPP = get_unsafe_type_ptr(TP)
                rffi.cast(TPP, target)[index] = rffi.cast(TP, source)
                return
    raise NotImplementedError("bad integer size")

def unsafe_write_raw_unsigned_data(w_cdata, index, source, size):
    with w_cdata as target:
        for TP, _ in misc._prim_unsigned_types:
            if size == rffi.sizeof(TP):
                TPP = get_unsafe_type_ptr(TP)
                rffi.cast(TPP, target)[index] = rffi.cast(TP, source)
                return
    raise NotImplementedError("bad integer size")

def unsafe_write_raw_float_data(w_cdata, index, source, size):
    with w_cdata as target:
        for TP, _ in misc._prim_float_types:
            if size == rffi.sizeof(TP):
                TPP = get_unsafe_type_ptr(TP)
                rffi.cast(TPP, target)[index] = rffi.cast(TP, source)
                return
    raise NotImplementedError("bad float size")


@unwrap_spec(w_cdata=cdataobj.W_CData, index=int)
def unsafe_write(space, w_cdata, index, w_value):
    ctype = w_cdata.ctype
    if not isinstance(ctype, ctypeptr.W_CTypePtrOrArray):
        raise oefmt(space.w_TypeError,
                    "expected a cdata of type pointer or array")
    ctitem = ctype.ctitem

    if isinstance(ctitem, ctypeprim.W_CTypePrimitiveChar):
        charvalue = ctitem._convert_to_char(w_value)
        unsafe_write_raw_signed_data(w_cdata, index, ord(charvalue), size=1)
        return

    if isinstance(ctitem, ctypeprim.W_CTypePrimitiveSigned):
        if ctitem.value_fits_long:
            value = ctitem._convert_to_long(w_value)
            unsafe_write_raw_signed_data(w_cdata, index, value, ctitem.size)
            return

    if isinstance(ctitem, ctypeprim.W_CTypePrimitiveUnsigned):
        if ctitem.value_fits_ulong:
            value = ctitem._convert_to_ulong(w_value)
            unsafe_write_raw_unsigned_data(w_cdata, index, value, ctitem.size)
            return

    if isinstance(ctitem, ctypeprim.W_CTypePrimitiveFloat):
        if not isinstance(ctitem, ctypeprim.W_CTypePrimitiveLongDouble):
            value = ctitem._convert_to_double(w_value)
            unsafe_write_raw_float_data(w_cdata, index, value, ctitem.size)
            return

    raise oefmt(space.w_TypeError, "unsupported type in unsafe_write(): '%s'",
                ctitem.name)

# ____________________________________________________________


def unsafe_read_raw_signed_data(w_cdata, index, size):
    with w_cdata as target:
        for TP, _ in misc._prim_signed_types:
            if size == rffi.sizeof(TP):
                TPP = get_unsafe_type_ptr(TP)
                value = rffi.cast(TPP, target)[index]
                return rffi.cast(lltype.Signed, value)
    raise NotImplementedError("bad integer size")

def unsafe_read_raw_unsigned_data(w_cdata, index, size):
    with w_cdata as target:
        for TP, _ in misc._prim_unsigned_types:
            if size == rffi.sizeof(TP):
                TPP = get_unsafe_type_ptr(TP)
                value = rffi.cast(TPP, target)[index]
                return rffi.cast(lltype.Unsigned, value)
    raise NotImplementedError("bad integer size")

def unsafe_read_raw_float_data(w_cdata, index, size):
    with w_cdata as target:
        for TP, _ in misc._prim_float_types:
            if size == rffi.sizeof(TP):
                TPP = get_unsafe_type_ptr(TP)
                value = rffi.cast(TPP, target)[index]
                return rffi.cast(lltype.Float, value)
    raise NotImplementedError("bad integer size")


@unwrap_spec(w_cdata=cdataobj.W_CData, index=int)
def unsafe_read(space, w_cdata, index):
    ctype = w_cdata.ctype
    if not isinstance(ctype, ctypeptr.W_CTypePtrOrArray):
        raise oefmt(space.w_TypeError,
                    "expected a cdata of type pointer or array")
    ctitem = ctype.ctitem

    if isinstance(ctitem, ctypeprim.W_CTypePrimitiveChar):
        uintvalue = unsafe_read_raw_unsigned_data(w_cdata, index, size=1)
        return space.wrap(chr(intmask(uintvalue)))

    if isinstance(ctitem, ctypeprim.W_CTypePrimitiveSigned):
        if ctitem.value_fits_long:
            intvalue = unsafe_read_raw_signed_data(w_cdata, index, ctitem.size)
            return space.wrap(intvalue)

    if isinstance(ctitem, ctypeprim.W_CTypePrimitiveUnsigned):
        if ctitem.value_fits_ulong:
            uintvalue = unsafe_read_raw_unsigned_data(w_cdata, index,
                                                      ctitem.size)
            return space.wrap(uintvalue)

    if isinstance(ctitem, ctypeprim.W_CTypePrimitiveFloat):
        if not isinstance(ctitem, ctypeprim.W_CTypePrimitiveLongDouble):
            floatvalue = unsafe_read_raw_float_data(w_cdata, index, ctitem.size)
            return space.wrap(floatvalue)

    raise oefmt(space.w_TypeError, "unsupported type in unsafe_read(): '%s'",
                ctitem.name)
