"""
Function pointers.
"""

from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rlib import jit, clibffi
from pypy.rlib.objectmodel import we_are_translated, instantiate
from pypy.rlib.objectmodel import keepalive_until_here

from pypy.module._cffi_backend.ctypeobj import W_CType
from pypy.module._cffi_backend.ctypeptr import W_CTypePtrBase
from pypy.module._cffi_backend.ctypevoid import W_CTypeVoid
from pypy.module._cffi_backend import ctypeprim, ctypestruct, ctypearray
from pypy.module._cffi_backend import cdataobj


class W_CTypeFunc(W_CTypePtrBase):

    def __init__(self, space, fargs, fresult, ellipsis):
        self.cif_descr = lltype.nullptr(CIF_DESCRIPTION)
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
                ct = w_obj.ctype
                if isinstance(ct, ctypearray.W_CTypeArray):
                    ct = ct.ctptr
            else:
                raise operationerrfmt(space.w_TypeError,
                             "argument %d passed in the variadic part "
                             "needs to be a cdata object (got %s)",
                             i + 1, space.type(w_obj).getname(space))
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


    def call(self, funcaddr, args_w):
        space = self.space
        cif_descr = self.cif_descr
        nargs_declared = len(self.fargs)

        if cif_descr:
            # regular case: this function does not take '...' arguments
            if len(args_w) != nargs_declared:
                raise operationerrfmt(space.w_TypeError,
                                      "'%s' expects %d arguments, got %d",
                                      self.name, nargs_declared, len(args_w))
        else:
            # call of a variadic function
            if len(args_w) < nargs_declared:
                raise operationerrfmt(space.w_TypeError,
                                    "%s expects at least %d arguments, got %d",
                                      self.name, nargs_declared, len(args_w))
            self = self.new_ctypefunc_completing_argtypes(args_w)
            cif_descr = self.cif_descr

        size = cif_descr.exchange_size
        mustfree_count_plus_1 = 0
        buffer = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw')
        try:
            buffer_array = rffi.cast(rffi.VOIDPP, buffer)
            for i in range(len(args_w)):
                data = rffi.ptradd(buffer, cif_descr.exchange_args[i])
                buffer_array[i] = data
                w_obj = args_w[i]
                argtype = self.fargs[i]
                #
                # special-case for strings.  xxx should avoid copying
                if argtype.is_char_ptr_or_array:
                    try:
                        s = space.str_w(w_obj)
                    except OperationError, e:
                        if not e.match(space, space.w_TypeError):
                            raise
                    else:
                        raw_string = rffi.str2charp(s)
                        rffi.cast(rffi.CCHARPP, data)[0] = raw_string
                        # set the "must free" flag to 1
                        set_mustfree_flag(data, 1)
                        mustfree_count_plus_1 = i + 1
                        continue   # skip the convert_from_object()

                    # set the "must free" flag to 0
                    set_mustfree_flag(data, 0)
                #
                argtype.convert_from_object(data, w_obj)
            resultdata = rffi.ptradd(buffer, cif_descr.exchange_result)

            clibffi.c_ffi_call(cif_descr.cif,
                               rffi.cast(rffi.VOIDP, funcaddr),
                               resultdata,
                               buffer_array)

            if isinstance(self.ctitem, W_CTypeVoid):
                w_res = space.w_None
            else:
                w_res = self.ctitem.convert_to_object(resultdata)
        finally:
            for i in range(mustfree_count_plus_1):
                argtype = self.fargs[i]
                if argtype.is_char_ptr_or_array:
                    data = rffi.ptradd(buffer, cif_descr.exchange_args[i])
                    if get_mustfree_flag(data):
                        raw_string = rffi.cast(rffi.CCHARPP, data)[0]
                        lltype.free(raw_string, flavor='raw')
            lltype.free(buffer, flavor='raw')
        return w_res

def get_mustfree_flag(data):
    return ord(rffi.ptradd(data, -1)[0])

def set_mustfree_flag(data, flag):
    rffi.ptradd(data, -1)[0] = chr(flag)

# ____________________________________________________________

# The "cif" is a block of raw memory describing how to do a call via libffi.
# It starts with a block of memory of type FFI_CIF, which is used by libffi
# itself.  Following it, we find _cffi_backend-specific information:
#
#  - 'exchange_size': an integer that tells how big a buffer we must
#    allocate for the call; this buffer should start with an array of
#    pointers to the actual argument values.
#
#  - 'exchange_result': the offset in that buffer for the result of the call.
#
#  - 'exchange_args[nargs]': the offset in that buffer for each argument.
#
# Following this, we have other data structures for libffi (with direct
# pointers from the FFI_CIF to these data structures):
#
#  - the argument types, as an array of 'ffi_type *'.
#
#  - optionally, the result's and the arguments' ffi type data
#    (this is used only for 'struct' ffi types; in other cases the
#    'ffi_type *' just points to static data like 'ffi_type_sint32').

FFI_CIF = clibffi.FFI_CIFP.TO
FFI_TYPE = clibffi.FFI_TYPE_P.TO
FFI_TYPE_P = clibffi.FFI_TYPE_P
FFI_TYPE_PP = clibffi.FFI_TYPE_PP
SIZE_OF_FFI_ARG = 8     # good enough

CIF_DESCRIPTION = lltype.Struct(
    'CIF_DESCRIPTION',
    ('cif', FFI_CIF),
    ('exchange_size', lltype.Signed),
    ('exchange_result', lltype.Signed),
    ('exchange_args', rffi.CArray(lltype.Signed)))

CIF_DESCRIPTION_P = lltype.Ptr(CIF_DESCRIPTION)

# We attach (lazily or not) to the classes or instances a 'ffi_type' attribute
W_CType.ffi_type = lltype.nullptr(FFI_TYPE_P.TO)
W_CTypePtrBase.ffi_type = clibffi.ffi_type_pointer
W_CTypeVoid.ffi_type = clibffi.ffi_type_void

def _settype(ctype, ffi_type):
    ctype.ffi_type = ffi_type
    return ffi_type


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


    def fb_fill_type(self, ctype):
        if ctype.ffi_type:   # common case: the ffi_type was already computed
            return ctype.ffi_type

        space = self.space
        size = ctype.size
        if size < 0:
            raise operationerrfmt(space.w_TypeError,
                                  "ctype '%s' has incomplete type",
                                  ctype.name)

        if isinstance(ctype, ctypestruct.W_CTypeStruct):

            # We can't pass a struct that was completed by verify().
            # Issue: assume verify() is given "struct { long b; ...; }".
            # Then it will complete it in the same way whether it is actually
            # "struct { long a, b; }" or "struct { double a; long b; }".
            # But on 64-bit UNIX, these two structs are passed by value
            # differently: e.g. on x86-64, "b" ends up in register "rsi" in
            # the first case and "rdi" in the second case.
            if ctype.custom_field_pos:
                raise OperationError(space.w_TypeError,
                                     space.wrap(
                   "cannot pass as an argument a struct that was completed "
                   "with verify() (see pypy/module/_cffi_backend/ctypefunc.py "
                   "for details)"))

            # allocate an array of (n + 1) ffi_types
            n = len(ctype.fields_list)
            elements = self.fb_alloc(rffi.sizeof(FFI_TYPE_P) * (n + 1))
            elements = rffi.cast(FFI_TYPE_PP, elements)

            # fill it with the ffi types of the fields
            for i, cf in enumerate(ctype.fields_list):
                if cf.is_bitfield():
                    raise OperationError(space.w_NotImplementedError,
                        space.wrap("cannot pass as argument a struct "
                                   "with bit fields"))
                ffi_subtype = self.fb_fill_type(cf.ctype)
                if elements:
                    elements[i] = ffi_subtype

            # zero-terminate the array
            if elements:
                elements[n] = lltype.nullptr(FFI_TYPE_P.TO)

            # allocate and fill an ffi_type for the struct itself
            ffistruct = self.fb_alloc(rffi.sizeof(FFI_TYPE))
            ffistruct = rffi.cast(FFI_TYPE_P, ffistruct)
            if ffistruct:
                rffi.setintfield(ffistruct, 'c_size', size)
                rffi.setintfield(ffistruct, 'c_alignment', ctype.alignof())
                rffi.setintfield(ffistruct, 'c_type', clibffi.FFI_TYPE_STRUCT)
                ffistruct.c_elements = elements

            return ffistruct

        elif isinstance(ctype, ctypeprim.W_CTypePrimitiveSigned):
            # compute lazily once the ffi_type
            if   size == 1: return _settype(ctype, clibffi.ffi_type_sint8)
            elif size == 2: return _settype(ctype, clibffi.ffi_type_sint16)
            elif size == 4: return _settype(ctype, clibffi.ffi_type_sint32)
            elif size == 8: return _settype(ctype, clibffi.ffi_type_sint64)

        elif (isinstance(ctype, ctypeprim.W_CTypePrimitiveChar) or
              isinstance(ctype, ctypeprim.W_CTypePrimitiveUnsigned)):
            if   size == 1: return _settype(ctype, clibffi.ffi_type_uint8)
            elif size == 2: return _settype(ctype, clibffi.ffi_type_uint16)
            elif size == 4: return _settype(ctype, clibffi.ffi_type_uint32)
            elif size == 8: return _settype(ctype, clibffi.ffi_type_uint64)

        elif isinstance(ctype, ctypeprim.W_CTypePrimitiveFloat):
            if   size == 4: return _settype(ctype, clibffi.ffi_type_float)
            elif size == 8: return _settype(ctype, clibffi.ffi_type_double)

        raise operationerrfmt(space.w_NotImplementedError,
                              "ctype '%s' (size %d) not supported as argument"
                              " or return value",
                              ctype.name, size)


    def fb_build(self):
        nargs = len(self.fargs)

        # start with a cif_description (cif and exchange_* fields)
        self.fb_alloc(llmemory.sizeof(CIF_DESCRIPTION, nargs))

        # next comes an array of 'ffi_type*', one per argument
        atypes = self.fb_alloc(rffi.sizeof(FFI_TYPE_P) * nargs)
        self.atypes = rffi.cast(FFI_TYPE_PP, atypes)

        # next comes the result type data
        self.rtype = self.fb_fill_type(self.fresult)

        # next comes each argument's type data
        for i, farg in enumerate(self.fargs):
            atype = self.fb_fill_type(farg)
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

        # then enough room for the result --- which means at least
        # sizeof(ffi_arg), according to the ffi docs (this is 8).
        exchange_offset += max(rffi.getintfield(self.rtype, 'c_size'),
                               SIZE_OF_FFI_ARG)

        # loop over args
        for i, farg in enumerate(self.fargs):
            if farg.is_char_ptr_or_array:
                exchange_offset += 1   # for the "must free" flag
            exchange_offset = self.align_arg(exchange_offset)
            cif_descr.exchange_args[i] = exchange_offset
            exchange_offset += rffi.getintfield(self.atypes[i], 'c_size')

        # store the exchange data size
        cif_descr.exchange_size = exchange_offset


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
        self.fb_build_exchange(ctypefunc.cif_descr)

        # call libffi's ffi_prep_cif() function
        res = clibffi.c_ffi_prep_cif(rawmem.cif, clibffi.FFI_DEFAULT_ABI,
                                     len(self.fargs),
                                     self.rtype, self.atypes)
        if rffi.cast(lltype.Signed, res) != clibffi.FFI_OK:
            raise OperationError(space.w_SystemError,
                space.wrap("libffi failed to build this function type"))
