from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import keepalive_until_here
from pypy.rlib import rgc

from pypy.module._ffi_backend import misc


class W_CData(Wrappable):
    _immutable_ = True
    cdata = lltype.nullptr(rffi.CCHARP.TO)

    def __init__(self, space, cdata, ctype):
        from pypy.module._ffi_backend import ctypeobj
        assert lltype.typeOf(cdata) == rffi.CCHARP
        assert isinstance(ctype, ctypeobj.W_CType)
        self.space = space
        self.cdata = cdata
        self.ctype = ctype

    def repr(self):
        return self.space.wrap("<cdata '%s'>" % self.ctype.name)

    def int(self):
        return self.ctype.int(self)

    def read_raw_signed_data(self):
        result = misc.read_raw_signed_data(self.cdata, self.ctype.size)
        keepalive_until_here(self)
        return result

    def read_raw_unsigned_data(self):
        result = misc.read_raw_unsigned_data(self.cdata, self.ctype.size)
        keepalive_until_here(self)
        return result

    def write_raw_integer_data(self, source):
        misc.write_raw_integer_data(self.cdata, source, self.ctype.size)
        keepalive_until_here(self)


class W_CDataOwn(W_CData):

    def __init__(self, space, size, ctype):
        cdata = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw')
        W_CData.__init__(self, space, cdata, ctype)

    @rgc.must_be_light_finalizer
    def __del__(self):
        lltype.free(self.cdata, flavor='raw')


W_CData.typedef = TypeDef(
    '_ffi_backend.CData',
    __repr__ = interp2app(W_CData.repr),
    __int__ = interp2app(W_CData.int),
    )
W_CData.acceptable_as_base_class = False


def check_cdata(space, w_obj):
    return space.is_w(space.type(w_obj), space.gettypefor(W_CData))
