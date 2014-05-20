"""
Function pointers.
"""

import sys

from rpython.rlib import jit, clibffi, jit_libffi
from rpython.rlib.jit_libffi import (CIF_DESCRIPTION, CIF_DESCRIPTION_P,
    FFI_TYPE, FFI_TYPE_P, FFI_TYPE_PP, SIZE_OF_FFI_ARG)
from rpython.rlib.objectmodel import we_are_translated, instantiate
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi

from pypy.interpreter.error import OperationError, oefmt
from pypy.module._cffi_backend import ctypearray, cdataobj, cerrno
from pypy.module._cffi_backend.ctypeobj import W_CType
from pypy.module._cffi_backend.ctypeptr import W_CTypePtrBase, W_CTypePointer
from pypy.module._cffi_backend.ctypevoid import W_CTypeVoid
from pypy.module._cffi_backend.ctypestruct import W_CTypeStruct
from pypy.module._cffi_backend.ctypeprim import (W_CTypePrimitiveSigned,
    W_CTypePrimitiveUnsigned, W_CTypePrimitiveCharOrUniChar,
    W_CTypePrimitiveFloat, W_CTypePrimitiveLongDouble)


class W_CTypeFunc(W_CTypePtrBase):
    _attrs_            = ['fargs', 'ellipsis', 'cif_descr']
    _immutable_fields_ = ['fargs[*]', 'ellipsis', 'cif_descr']
    kind = "function"

    def __init__(self, space, fargs, fresult, ellipsis):
        extra = self._compute_extra_text(fargs, fresult, ellipsis)
        size = rffi.sizeof(rffi.VOIDP)
        W_CTypePtrBase.__init__(self, space, size, extra, 2, fresult,
                                could_cast_anything=False)
        self.fargs = fargs
        self.ellipsis = bool(ellipsis)
        # fresult is stored in self.ctitem

        if not ellipsis:
            # Functions with '...' varargs are stored without a cif_descr
            # at all.  The cif is computed on every call from the actual
            # types passed in.  For all other functions, the cif_descr
            # is computed here.
            CifDescrBuilder(fargs, fresult).rawallocate(self)

    def new_ctypefunc_completing_argtypes(self, args_w):
        space = self.space
        nargs_declared = len(self.fargs)
        fvarargs = [None] * len(args_w)
        fvarargs[:nargs_declared] = self.fargs
        for i in range(nargs_declared, len(args_w)):
            w_obj = args_w[i]
            if isinstance(w_obj, cdataobj.W_CData):
                ct = w_obj.ctype.get_vararg_type()
            else:
                raise oefmt(space.w_TypeError,
                            "argument %d passed in the variadic part needs to "
                            "be a cdata object (got %T)", i + 1, w_obj)
            fvarargs[i] = ct
        ctypefunc = instantiate(W_CTypeFunc)
        ctypefunc.space = space
        ctypefunc.fargs = fvarargs
        ctypefunc.ctitem = self.ctitem
        CifDescrBuilder(fvarargs, self.ctitem).rawallocate(ctypefunc)
        return ctypefunc

    def __del__(self):
        if self.cif_descr:
            lltype.free(self.cif_descr, flavor='raw')

    def _compute_extra_text(self, fargs, fresult, ellipsis):
        argnames = ['(*)(']
        for i, farg in enumerate(fargs):
            if i > 0:
                argnames.append(', ')
            argnames.append(farg.name)
        if ellipsis:
            if len(fargs) > 0:
                argnames.append(', ')
            argnames.append('...')
        argnames.append(')')
        return ''.join(argnames)

    def _fget(self, attrchar):
        if attrchar == 'a':    # args
            return self.space.newtuple([self.space.wrap(a)
                                        for a in self.fargs])
        if attrchar == 'r':    # result
            return self.space.wrap(self.ctitem)
        if attrchar == 'E':    # ellipsis
            return self.space.wrap(self.ellipsis)
        if attrchar == 'A':    # abi
            return self.space.wrap(clibffi.FFI_DEFAULT_ABI)     # XXX
        return W_CTypePtrBase._fget(self, attrchar)

    def call(self, funcaddr, args_w):
        if self.cif_descr:
            # regular case: this function does not take '...' arguments
            self = jit.promote(self)
            nargs_declared = len(self.fargs)
            if len(args_w) != nargs_declared:
                space = self.space
                raise oefmt(space.w_TypeError,
                            "'%s' expects %d arguments, got %d",
                            self.name, nargs_declared, len(args_w))
            return self._call(funcaddr, args_w)
        else:
            # call of a variadic function
            return self.call_varargs(funcaddr, args_w)

    @jit.dont_look_inside
    def call_varargs(self, funcaddr, args_w):
        nargs_declared = len(self.fargs)
        if len(args_w) < nargs_declared:
            space = self.space
            raise oefmt(space.w_TypeError,
                        "'%s' expects at least %d arguments, got %d",
                        self.name, nargs_declared, len(args_w))
        completed = self.new_ctypefunc_completing_argtypes(args_w)
        return completed._call(funcaddr, args_w)

    # The following is the core of function calls.  It is @unroll_safe,
    # which means that the JIT is free to unroll the argument handling.
    # But in case the function takes variable arguments, we don't unroll
    # this (yet) for better safety: this is handled by @dont_look_inside
    # in call_varargs.
    @jit.unroll_safe
    def _call(self, funcaddr, args_w):
        space = self.space
        cif_descr = self.cif_descr
        size = cif_descr.exchange_size
        mustfree_max_plus_1 = 0
        buffer = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw')
        try:
            for i in range(len(args_w)):
                data = rffi.ptradd(buffer, cif_descr.exchange_args[i])
                w_obj = args_w[i]
                argtype = self.fargs[i]
                if argtype.convert_argument_from_object(data, w_obj):
                    # argtype is a pointer type, and w_obj a list/tuple/str
                    mustfree_max_plus_1 = i + 1

            ec = cerrno.get_errno_container(space)
            cerrno.restore_errno_from(ec)
            jit_libffi.jit_ffi_call(cif_descr,
                                    rffi.cast(rffi.VOIDP, funcaddr),
                                    buffer)
            e = cerrno.get_real_errno()
            cerrno.save_errno_into(ec, e)

            resultdata = rffi.ptradd(buffer, cif_descr.exchange_result)
            w_res = self.ctitem.copy_and_convert_to_object(resultdata)
        finally:
            for i in range(mustfree_max_plus_1):
                argtype = self.fargs[i]
                if isinstance(argtype, W_CTypePointer):
                    data = rffi.ptradd(buffer, cif_descr.exchange_args[i])
                    flag = get_mustfree_flag(data)
                    if flag == 1:
                        raw_string = rffi.cast(rffi.CCHARPP, data)[0]
                        lltype.free(raw_string, flavor='raw')
            lltype.free(buffer, flavor='raw')
        return w_res

def get_mustfree_flag(data):
    return ord(rffi.ptradd(data, -1)[0])

def set_mustfree_flag(data, flag):
    rffi.ptradd(data, -1)[0] = chr(flag)

def _get_abi(space, name):
    abi = getattr(clibffi, name)
    assert isinstance(abi, int)
    return space.wrap(abi)

# ____________________________________________________________


W_CTypeFunc.cif_descr = lltype.nullptr(CIF_DESCRIPTION)     # default value

BIG_ENDIAN = sys.byteorder == 'big'
USE_C_LIBFFI_MSVC = getattr(clibffi, 'USE_C_LIBFFI_MSVC', False)


# ----------
# We attach to the classes small methods that return a 'ffi_type'
def _missing_ffi_type(self, cifbuilder, is_result_type):
    space = self.space
    if self.size < 0:
        raise oefmt(space.w_TypeError,
                    "ctype '%s' has incomplete type", self.name)
    if is_result_type:
        place = "return value"
    else:
        place = "argument"
    raise oefmt(space.w_NotImplementedError,
                "ctype '%s' (size %d) not supported as %s",
                self.name, self.size, place)

def _struct_ffi_type(self, cifbuilder, is_result_type):
    if self.size >= 0:
        return cifbuilder.fb_struct_ffi_type(self, is_result_type)
    return _missing_ffi_type(self, cifbuilder, is_result_type)

def _primsigned_ffi_type(self, cifbuilder, is_result_type):
    size = self.size
    if   size == 1: return clibffi.ffi_type_sint8
    elif size == 2: return clibffi.ffi_type_sint16
    elif size == 4: return clibffi.ffi_type_sint32
    elif size == 8: return clibffi.ffi_type_sint64
    return _missing_ffi_type(self, cifbuilder, is_result_type)

def _primunsigned_ffi_type(self, cifbuilder, is_result_type):
    size = self.size
    if   size == 1: return clibffi.ffi_type_uint8
    elif size == 2: return clibffi.ffi_type_uint16
    elif size == 4: return clibffi.ffi_type_uint32
    elif size == 8: return clibffi.ffi_type_uint64
    return _missing_ffi_type(self, cifbuilder, is_result_type)

def _primfloat_ffi_type(self, cifbuilder, is_result_type):
    size = self.size
    if   size == 4: return clibffi.ffi_type_float
    elif size == 8: return clibffi.ffi_type_double
    return _missing_ffi_type(self, cifbuilder, is_result_type)

def _primlongdouble_ffi_type(self, cifbuilder, is_result_type):
    return clibffi.ffi_type_longdouble

def _ptr_ffi_type(self, cifbuilder, is_result_type):
    return clibffi.ffi_type_pointer

def _void_ffi_type(self, cifbuilder, is_result_type):
    if is_result_type:
        return clibffi.ffi_type_void
    return _missing_ffi_type(self, cifbuilder, is_result_type)

W_CType._get_ffi_type                       = _missing_ffi_type
W_CTypeStruct._get_ffi_type                 = _struct_ffi_type
W_CTypePrimitiveSigned._get_ffi_type        = _primsigned_ffi_type
W_CTypePrimitiveCharOrUniChar._get_ffi_type = _primunsigned_ffi_type
W_CTypePrimitiveUnsigned._get_ffi_type      = _primunsigned_ffi_type
W_CTypePrimitiveFloat._get_ffi_type         = _primfloat_ffi_type
W_CTypePrimitiveLongDouble._get_ffi_type    = _primlongdouble_ffi_type
W_CTypePtrBase._get_ffi_type                = _ptr_ffi_type
W_CTypeVoid._get_ffi_type                   = _void_ffi_type
# ----------


class CifDescrBuilder(object):
    rawmem = lltype.nullptr(rffi.CCHARP.TO)

    def __init__(self, fargs, fresult):
        self.fargs = fargs
        self.fresult = fresult

    def fb_alloc(self, size):
        size = llmemory.raw_malloc_usage(size)
        if not self.bufferp:
            self.nb_bytes += size
            return lltype.nullptr(rffi.CCHARP.TO)
        else:
            result = self.bufferp
            self.bufferp = rffi.ptradd(result, size)
            return result

    def fb_fill_type(self, ctype, is_result_type):
        return ctype._get_ffi_type(self, is_result_type)

    def fb_struct_ffi_type(self, ctype, is_result_type=False):
        # We can't pass a struct that was completed by verify().
        # Issue: assume verify() is given "struct { long b; ...; }".
        # Then it will complete it in the same way whether it is actually
        # "struct { long a, b; }" or "struct { double a; long b; }".
        # But on 64-bit UNIX, these two structs are passed by value
        # differently: e.g. on x86-64, "b" ends up in register "rsi" in
        # the first case and "rdi" in the second case.
        #
        # Another reason for 'custom_field_pos' would be anonymous
        # nested structures: we lost the information about having it
        # here, so better safe (and forbid it) than sorry (and maybe
        # crash).
        space = self.space
        if ctype.custom_field_pos:
            raise OperationError(space.w_TypeError,
                                 space.wrap(
               "cannot pass as an argument a struct that was completed "
               "with verify() (see pypy/module/_cffi_backend/ctypefunc.py "
               "for details)"))

        # walk the fields, expanding arrays into repetitions; first,
        # only count how many flattened fields there are
        nflat = 0
        for i, cf in enumerate(ctype.fields_list):
            if cf.is_bitfield():
                raise OperationError(space.w_NotImplementedError,
                    space.wrap("cannot pass as argument or return value "
                               "a struct with bit fields"))
            flat = 1
            ct = cf.ctype
            while isinstance(ct, ctypearray.W_CTypeArray):
                flat *= ct.length
                ct = ct.ctitem
            if flat <= 0:
                raise OperationError(space.w_NotImplementedError,
                    space.wrap("cannot pass as argument or return value "
                               "a struct with a zero-length array"))
            nflat += flat

        if USE_C_LIBFFI_MSVC and is_result_type:
            # MSVC returns small structures in registers.  Pretend int32 or
            # int64 return type.  This is needed as a workaround for what
            # is really a bug of libffi_msvc seen as an independent library
            # (ctypes has a similar workaround).
            if ctype.size <= 4:
                return clibffi.ffi_type_sint32
            if ctype.size <= 8:
                return clibffi.ffi_type_sint64

        # allocate an array of (nflat + 1) ffi_types
        elements = self.fb_alloc(rffi.sizeof(FFI_TYPE_P) * (nflat + 1))
        elements = rffi.cast(FFI_TYPE_PP, elements)

        # fill it with the ffi types of the fields
        nflat = 0
        for i, cf in enumerate(ctype.fields_list):
            flat = 1
            ct = cf.ctype
            while isinstance(ct, ctypearray.W_CTypeArray):
                flat *= ct.length
                ct = ct.ctitem
            ffi_subtype = self.fb_fill_type(ct, False)
            if elements:
                for j in range(flat):
                    elements[nflat] = ffi_subtype
                    nflat += 1

        # zero-terminate the array
        if elements:
            elements[nflat] = lltype.nullptr(FFI_TYPE_P.TO)

        # allocate and fill an ffi_type for the struct itself
        ffistruct = self.fb_alloc(rffi.sizeof(FFI_TYPE))
        ffistruct = rffi.cast(FFI_TYPE_P, ffistruct)
        if ffistruct:
            rffi.setintfield(ffistruct, 'c_size', ctype.size)
            rffi.setintfield(ffistruct, 'c_alignment', ctype.alignof())
            rffi.setintfield(ffistruct, 'c_type', clibffi.FFI_TYPE_STRUCT)
            ffistruct.c_elements = elements

        return ffistruct

    def fb_build(self):
        # Build a CIF_DESCRIPTION.  Actually this computes the size and
        # allocates a larger amount of data.  It starts with a
        # CIF_DESCRIPTION and continues with data needed for the CIF:
        #
        #  - the argument types, as an array of 'ffi_type *'.
        #
        #  - optionally, the result's and the arguments' ffi type data
        #    (this is used only for 'struct' ffi types; in other cases the
        #    'ffi_type *' just points to static data like 'ffi_type_sint32').
        #
        nargs = len(self.fargs)

        # start with a cif_description (cif and exchange_* fields)
        self.fb_alloc(llmemory.sizeof(CIF_DESCRIPTION, nargs))

        # next comes an array of 'ffi_type*', one per argument
        atypes = self.fb_alloc(rffi.sizeof(FFI_TYPE_P) * nargs)
        self.atypes = rffi.cast(FFI_TYPE_PP, atypes)

        # next comes the result type data
        self.rtype = self.fb_fill_type(self.fresult, True)

        # next comes each argument's type data
        for i, farg in enumerate(self.fargs):
            atype = self.fb_fill_type(farg, False)
            if self.atypes:
                self.atypes[i] = atype

    def align_arg(self, n):
        return (n + 7) & ~7

    def fb_build_exchange(self, cif_descr):
        nargs = len(self.fargs)

        # first, enough room for an array of 'nargs' pointers
        exchange_offset = rffi.sizeof(rffi.CCHARP) * nargs
        exchange_offset = self.align_arg(exchange_offset)
        cif_descr.exchange_result = exchange_offset
        cif_descr.exchange_result_libffi = exchange_offset

        if BIG_ENDIAN and self.fresult.is_primitive_integer:
            # For results of precisely these types, libffi has a
            # strange rule that they will be returned as a whole
            # 'ffi_arg' if they are smaller.  The difference
            # only matters on big-endian.
            if self.fresult.size < SIZE_OF_FFI_ARG:
                diff = SIZE_OF_FFI_ARG - self.fresult.size
                cif_descr.exchange_result += diff

        # then enough room for the result, rounded up to sizeof(ffi_arg)
        exchange_offset += max(rffi.getintfield(self.rtype, 'c_size'),
                               SIZE_OF_FFI_ARG)

        # loop over args
        for i, farg in enumerate(self.fargs):
            if isinstance(farg, W_CTypePointer):
                exchange_offset += 1   # for the "must free" flag
            exchange_offset = self.align_arg(exchange_offset)
            cif_descr.exchange_args[i] = exchange_offset
            exchange_offset += rffi.getintfield(self.atypes[i], 'c_size')

        # store the exchange data size
        cif_descr.exchange_size = exchange_offset

    def fb_extra_fields(self, cif_descr):
        cif_descr.abi = clibffi.FFI_DEFAULT_ABI    # XXX
        cif_descr.nargs = len(self.fargs)
        cif_descr.rtype = self.rtype
        cif_descr.atypes = self.atypes

    @jit.dont_look_inside
    def rawallocate(self, ctypefunc):
        space = ctypefunc.space
        self.space = space

        # compute the total size needed in the CIF_DESCRIPTION buffer
        self.nb_bytes = 0
        self.bufferp = lltype.nullptr(rffi.CCHARP.TO)
        self.fb_build()

        # allocate the buffer
        if we_are_translated():
            rawmem = lltype.malloc(rffi.CCHARP.TO, self.nb_bytes,
                                   flavor='raw')
            rawmem = rffi.cast(CIF_DESCRIPTION_P, rawmem)
        else:
            # gross overestimation of the length below, but too bad
            rawmem = lltype.malloc(CIF_DESCRIPTION_P.TO, self.nb_bytes,
                                   flavor='raw')

        # the buffer is automatically managed from the W_CTypeFunc instance
        ctypefunc.cif_descr = rawmem

        # call again fb_build() to really build the libffi data structures
        self.bufferp = rffi.cast(rffi.CCHARP, rawmem)
        self.fb_build()
        assert self.bufferp == rffi.ptradd(rffi.cast(rffi.CCHARP, rawmem),
                                           self.nb_bytes)

        # fill in the 'exchange_*' fields
        self.fb_build_exchange(rawmem)

        # fill in the extra fields
        self.fb_extra_fields(rawmem)

        # call libffi's ffi_prep_cif() function
        res = jit_libffi.jit_ffi_prep_cif(rawmem)
        if res != clibffi.FFI_OK:
            raise OperationError(space.w_SystemError,
                space.wrap("libffi failed to build this function type"))
