from __future__ import with_statement
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rdynload import DLLHANDLE, dlopen, dlsym, dlclose, DLOpenError

from pypy.module._cffi_backend.cdataobj import W_CData
from pypy.module._cffi_backend.ctypefunc import W_CTypeFunc


class W_Library(Wrappable):
    handle = rffi.cast(DLLHANDLE, 0)

    def __init__(self, space, filename):
        self.space = space
        with rffi.scoped_str2charp(filename) as ll_libname:
            try:
                self.handle = dlopen(ll_libname)
            except DLOpenError, e:
                raise operationerrfmt(space.w_OSError,
                                      "cannot load '%s': %s",
                                      filename, e.msg)
        self.name = filename

    def __del__(self):
        h = self.handle
        if h != rffi.cast(DLLHANDLE, 0):
            self.handle = rffi.cast(DLLHANDLE, 0)
            dlclose(h)

    def repr(self):
        space = self.space
        return space.wrap("<clibrary '%s'>" % self.name)

    @unwrap_spec(ctypefunc=W_CTypeFunc, name=str)
    def load_function(self, ctypefunc, name):
        space = self.space
        cdata = dlsym(self.handle, name)
        if not cdata:
            raise operationerrfmt(space.w_KeyError,
                                  "function '%s' not found in library '%s'",
                                  name, self.name)
        return W_CData(space, rffi.cast(rffi.CCHARP, cdata), ctypefunc)


W_Library.typedef = TypeDef(
    '_cffi_backend.Library',
    __repr__ = interp2app(W_Library.repr),
    load_function = interp2app(W_Library.load_function),
    )
W_Library.acceptable_as_base_class = False


@unwrap_spec(filename=str)
def load_library(space, filename):
    lib = W_Library(space, filename)
    return space.wrap(lib)
