import operator
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import keepalive_until_here, specialize
from pypy.rlib import objectmodel, rgc

from pypy.module._ffi_backend import misc


class W_CData(Wrappable):
    _immutable_ = True
    cdata = lltype.nullptr(rffi.CCHARP.TO)

    def __init__(self, space, cdata, ctype):
        from pypy.module._ffi_backend import ctypeobj
        assert lltype.typeOf(cdata) == rffi.CCHARP
        assert isinstance(ctype, ctypeobj.W_CType)
        self.space = space
        self._cdata = cdata    # don't forget keepalive_until_here!
        self.ctype = ctype

    def repr(self):
        extra = self.extra_repr()
        return self.space.wrap("<cdata '%s'%s>" % (self.ctype.name, extra))

    def extra_repr(self):
        return ''

    def nonzero(self):
        return self.space.wrap(bool(self._cdata))

    def int(self):
        w_result = self.ctype.int(self._cdata)
        keepalive_until_here(self)
        return w_result

    def long(self):
        w_result = self.int()
        space = self.space
        if space.is_w(space.type(w_result), space.w_int):
            w_result = space.newlong(space.int_w(w_result))
        return w_result

    def float(self):
        w_result = self.ctype.float(self._cdata)
        keepalive_until_here(self)
        return w_result

    def len(self):
        from pypy.module._ffi_backend import ctypeobj
        space = self.space
        if isinstance(self.ctype, ctypeobj.W_CTypeArray):
            return space.wrap(self.get_array_length())
        raise operationerrfmt(space.w_TypeError,
                              "cdata of type '%s' has no len()",
                              self.ctype.name)

    def str(self):
        w_result = self.ctype.try_str(self._cdata)
        keepalive_until_here(self)
        return w_result or self.repr()

    @specialize.arg(2)
    def _cmp(self, w_other, cmp):
        space = self.space
        cdata1 = self._cdata
        other = space.interpclass_w(w_other)
        if isinstance(other, W_CData):
            cdata2 = other._cdata
        elif space.is_w(w_other, space.w_None):
            cdata2 = lltype.nullptr(rffi.CCHARP.TO)
        else:
            return space.w_NotImplemented
        return space.newbool(cmp(cdata1, cdata2))

    def eq(self, w_other): return self._cmp(w_other, operator.eq)
    def ne(self, w_other): return self._cmp(w_other, operator.ne)

    def hash(self):
        h = (objectmodel.compute_identity_hash(self.ctype) ^
             rffi.cast(lltype.Signed, self._cdata))
        return self.space.wrap(h)

    def getitem(self, w_index):
        space = self.space
        i = space.getindex_w(w_index, space.w_IndexError)
        self.ctype._check_subscript_index(self, i)
        ctitem = self.ctype.ctitem
        w_o = ctitem.convert_to_object(
            rffi.ptradd(self._cdata, i * ctitem.size))
        keepalive_until_here(self)
        return w_o

    def setitem(self, w_index, w_value):
        space = self.space
        i = space.getindex_w(w_index, space.w_IndexError)
        self.ctype._check_subscript_index(self, i)
        ctitem = self.ctype.ctitem
        ctitem.convert_from_object(
            rffi.ptradd(self._cdata, i * ctitem.size),
            w_value)
        keepalive_until_here(self)

    def read_raw_signed_data(self):
        result = misc.read_raw_signed_data(self._cdata, self.ctype.size)
        keepalive_until_here(self)
        return result

    def read_raw_unsigned_data(self):
        result = misc.read_raw_unsigned_data(self._cdata, self.ctype.size)
        keepalive_until_here(self)
        return result

    def write_raw_integer_data(self, source):
        misc.write_raw_integer_data(self._cdata, source, self.ctype.size)
        keepalive_until_here(self)

    def read_raw_float_data(self):
        result = misc.read_raw_float_data(self._cdata, self.ctype.size)
        keepalive_until_here(self)
        return result

    def write_raw_float_data(self, source):
        misc.write_raw_float_data(self._cdata, source, self.ctype.size)
        keepalive_until_here(self)

    def convert_to_object(self):
        w_obj = self.ctype.convert_to_object(self._cdata)
        keepalive_until_here(self)
        return w_obj

    def get_array_length(self):
        from pypy.module._ffi_backend import ctypeobj
        ctype = self.ctype
        assert isinstance(ctype, ctypeobj.W_CTypeArray)
        length = ctype.length
        assert length >= 0
        return length


class W_CDataOwnFromCasted(W_CData):

    def __init__(self, space, size, ctype):
        cdata = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw', zero=True)
        W_CData.__init__(self, space, cdata, ctype)

    @rgc.must_be_light_finalizer
    def __del__(self):
        lltype.free(self._cdata, flavor='raw')


class W_CDataOwn(W_CDataOwnFromCasted):

    def extra_repr(self):
        return ' owning %d bytes' % (self.ctype.size,)


class W_CDataOwnLength(W_CDataOwn):

    def __init__(self, space, size, ctype, length):
        W_CDataOwn.__init__(self, space, size, ctype)
        self.length = length

    def get_array_length(self):
        return self.length


W_CData.typedef = TypeDef(
    '_ffi_backend.CData',
    __repr__ = interp2app(W_CData.repr),
    __nonzero__ = interp2app(W_CData.nonzero),
    __int__ = interp2app(W_CData.int),
    __long__ = interp2app(W_CData.long),
    __float__ = interp2app(W_CData.float),
    __len__ = interp2app(W_CData.len),
    __str__ = interp2app(W_CData.str),
    __eq__ = interp2app(W_CData.eq),
    __ne__ = interp2app(W_CData.ne),
    __hash__ = interp2app(W_CData.hash),
    __getitem__ = interp2app(W_CData.getitem),
    __setitem__ = interp2app(W_CData.setitem),
    )
W_CData.acceptable_as_base_class = False
