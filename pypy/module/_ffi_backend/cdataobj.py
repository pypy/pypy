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
        extra = self.extra_repr()
        return self.space.wrap("<cdata '%s'%s>" % (self.ctype.name, extra))

    def extra_repr(self):
        return ''

    def nonzero(self):
        return self.space.wrap(bool(self.cdata))

    def int(self):
        w_result = self.ctype.int(self.cdata)
        keepalive_until_here(self)
        return w_result

    def long(self):
        w_result = self.int()
        space = self.space
        if space.is_w(space.type(w_result), space.w_int):
            w_result = space.newlong(space.int_w(w_result))
        return w_result

    def float(self):
        w_result = self.ctype.float(self.cdata)
        keepalive_until_here(self)
        return w_result

    def str(self):
        w_result = self.ctype.try_str(self.cdata)
        keepalive_until_here(self)
        return w_result or self.repr()

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

    def read_raw_float_data(self):
        result = misc.read_raw_float_data(self.cdata, self.ctype.size)
        keepalive_until_here(self)
        return result

    def write_raw_float_data(self, source):
        misc.write_raw_float_data(self.cdata, source, self.ctype.size)
        keepalive_until_here(self)

    def convert_to_object(self):
        w_obj = self.ctype.convert_to_object(self.cdata)
        keepalive_until_here(self)
        return w_obj


class W_CDataOwnFromCasted(W_CData):

    def __init__(self, space, size, ctype):
        cdata = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw', zero=True)
        W_CData.__init__(self, space, cdata, ctype)

    @rgc.must_be_light_finalizer
    def __del__(self):
        lltype.free(self.cdata, flavor='raw')


class W_CDataOwn(W_CDataOwnFromCasted):

    def extra_repr(self):
        return ' owning %d bytes' % (self.ctype.size,)



W_CData.typedef = TypeDef(
    '_ffi_backend.CData',
    __repr__ = interp2app(W_CData.repr),
    __nonzero__ = interp2app(W_CData.nonzero),
    __int__ = interp2app(W_CData.int),
    __long__ = interp2app(W_CData.long),
    __float__ = interp2app(W_CData.float),
    __str__ = interp2app(W_CData.str),
    )
W_CData.acceptable_as_base_class = False


def check_cdata(space, w_obj):
    return space.is_w(space.type(w_obj), space.gettypefor(W_CData))
