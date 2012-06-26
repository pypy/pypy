"""
Function pointers.
"""

from pypy.module._ffi_backend.ctypeptr import W_CTypePtrBase


class W_CTypeFunc(W_CTypePtrBase):

    def __init__(self, space, fargs, fresult, ellipsis):
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
        extra = ''.join(argnames)
        #
        W_CTypePtrBase.__init__(self, space, extra, 2, fresult)
        self.can_cast_anything = False
        self.ellipsis = ellipsis
        
        if not ellipsis:
            # Functions with '...' varargs are stored without a cif_descr
            # at all.  The cif is computed on every call from the actual
            # types passed in.  For all other functions, the cif_descr
            # is computed here.
            pass
