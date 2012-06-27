"""
Function pointers.
"""

from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rlib import jit, clibffi

from pypy.module._cffi_backend.ctypeptr import W_CTypePtrBase


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

    def __del__(self):
        if self.cif_descr:
            llmemory.raw_free(llmemory.cast_ptr_to_adr(self.cif_descr))

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
        if len(args_w) != len(self.fargs):
            raise operationerrfmt(space.w_TypeError,
                                  "'%s' expects %d arguments, got %d",
                                  self.name, len(self.fargs), len(args_w))
        xxx

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

CIF_DESCRIPTION = lltype.Struct(
    'CIF_DESCRIPTION',
    ('cif', FFI_CIF),
    ('exchange_size', lltype.Signed),
    ('exchange_result', lltype.Signed),
    ('exchange_args', lltype.Array(lltype.Signed)))

CIF_DESCRIPTION_P = lltype.Ptr(CIF_DESCRIPTION)


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
        xxx


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
        for farg in self.fargs:
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
        # sizeof(ffi_arg), according to the ffi docs (which is 8).
        exchange_offset += max(self.rtype.c_size, 8)

        # loop over args
        for i, farg in enumerate(self.fargs):
            exchange_offset = self.align_arg(exchange_offset)
            cif_descr.exchange_args[i] = exchange_offset
            exchange_offset += self.atypes[i].c_size

        # store the exchange data size
        cif_descr.exchange_size = exchange_offset


    @jit.dont_look_inside
    def rawallocate(self, ctypefunc):
        # compute the total size needed in the CIF_DESCRIPTION buffer
        self.nb_bytes = 0
        self.bufferp = lltype.nullptr(rffi.CCHARP.TO)
        self.fb_build()

        # allocate the buffer
        rawmem = rffi.cast(rffi.CCHARP,
                           llmemory.raw_malloc(self.nb_bytes))

        # the buffer is automatically managed from the W_CTypeFunc instance
        ctypefunc.cif_descr = rffi.cast(CIF_DESCRIPTION_P, rawmem)

        # call again fb_build() to really build the libffi data structures
        self.bufferp = rawmem
        self.fb_build()
        assert self.bufferp == rawmem + self.nb_bytes

        # fill in the 'exchange_*' fields
        self.fb_build_exchange(ctypefunc.cif_descr)

        # call libffi's ffi_prep_cif() function
        cif = rffi.cast(FFI_CIFP, rawmem)
        res = clibffi.c_ffi_prep_cif(cif, clibffi.FFI_DEFAULT_ABI,
                                     len(self.fargs),
                                     self.rtype, self.atypes)
        if rffi.cast(lltype.Signed, res) != clibffi.FFI_OK:
            space = ctypefunc.space
            raise OperationError(space.w_SystemError,
                space.wrap("libffi failed to build this function type"))
