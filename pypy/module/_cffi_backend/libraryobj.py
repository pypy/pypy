from __future__ import with_statement

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.module._rawffi.interp_rawffi import wrap_dlopenerror

from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.rdynload import DLLHANDLE, dlopen, dlsym, dlclose, DLOpenError

from pypy.module._cffi_backend.cdataobj import W_CData
from pypy.module._cffi_backend.ctypeobj import W_CType


class W_Library(W_Root):
    _immutable_ = True

    def __init__(self, space, filename, flags):
        self.space = space
        with rffi.scoped_str2charp(filename) as ll_libname:
            if filename is None:
                filename = "<None>"
            try:
                self.handle = dlopen(ll_libname, flags)
            except DLOpenError as e:
                raise wrap_dlopenerror(space, e, filename)
        self.name = filename
        self.register_finalizer(space)

    def _finalize_(self):
        h = self.handle
        if h != rffi.cast(DLLHANDLE, 0):
            self.handle = rffi.cast(DLLHANDLE, 0)
            dlclose(h)

    def repr(self):
        space = self.space
        return space.newtext("<clibrary '%s'>" % self.name)

    @unwrap_spec(w_ctype=W_CType, name='text')
    def load_function(self, w_ctype, name):
        from pypy.module._cffi_backend import ctypefunc, ctypeptr, ctypevoid
        space = self.space
        #
        ok = False
        if isinstance(w_ctype, ctypefunc.W_CTypeFunc):
            ok = True
        if (isinstance(w_ctype, ctypeptr.W_CTypePointer) and
            isinstance(w_ctype.ctitem, ctypevoid.W_CTypeVoid)):
            ok = True
        if not ok:
            raise oefmt(space.w_TypeError,
                        "function cdata expected, got '%s'", w_ctype.name)
        #
        try:
            cdata = dlsym(self.handle, name)
        except KeyError:
            raise oefmt(space.w_KeyError,
                        "function '%s' not found in library '%s'",
                        name, self.name)
        return W_CData(space, rffi.cast(rffi.CCHARP, cdata), w_ctype)

    @unwrap_spec(w_ctype=W_CType, name='text')
    def read_variable(self, w_ctype, name):
        space = self.space
        try:
            cdata = dlsym(self.handle, name)
        except KeyError:
            raise oefmt(space.w_KeyError,
                        "variable '%s' not found in library '%s'",
                        name, self.name)
        return w_ctype.convert_to_object(rffi.cast(rffi.CCHARP, cdata))

    @unwrap_spec(w_ctype=W_CType, name='text')
    def write_variable(self, w_ctype, name, w_value):
        space = self.space
        try:
            cdata = dlsym(self.handle, name)
        except KeyError:
            raise oefmt(space.w_KeyError,
                        "variable '%s' not found in library '%s'",
                        name, self.name)
        w_ctype.convert_from_object(rffi.cast(rffi.CCHARP, cdata), w_value)


W_Library.typedef = TypeDef(
    '_cffi_backend.Library',
    __repr__ = interp2app(W_Library.repr),
    load_function = interp2app(W_Library.load_function),
    read_variable = interp2app(W_Library.read_variable),
    write_variable = interp2app(W_Library.write_variable),
    )
W_Library.typedef.acceptable_as_base_class = False


@unwrap_spec(filename="str_or_None", flags=int)
def load_library(space, filename, flags=0):
    lib = W_Library(space, filename, flags)
    return lib
