"""
Function pointers.
"""

from pypy.rpython.lltypesystem import rffi
from pypy.rlib import clibffi

from pypy.module._cffi_backend.ctypeptr import W_CTypePtrBase


class W_CTypeFunc(W_CTypePtrBase):

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
            self.cif_descr = fb_prepare_cif(fargs, fresult)

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


CIF_DESCRIPTION = lltype.Struct(
    'CIF_DESCRIPTION',
    ('cif', clibffi.FFI_CIFP.TO),
    # the following information is used when doing the call:
    #  - a buffer of size 'exchange_size' is malloced
    #  - the arguments are converted from Python objects to raw data
    #  - the i'th raw data is stored at 'buffer + exchange_offset_arg[1+i]'
    #  - the call is done
    #  - the result is read back from 'buffer + exchange_offset_arg[0]'
    ('exchange_size', lltype.Signed),
    ('exchange_offset_arg', lltype.Array(lltype.Signed)))


def fb_prepare_cif(fargs, fresult):
    ...
