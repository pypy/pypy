from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import keepalive_until_here
from pypy.rlib import objectmodel, rgc

from pypy.module._cffi_backend import misc


class W_CData(Wrappable):
    _attrs_ = ['space', '_cdata', 'ctype']
    _immutable_ = True
    _cdata = lltype.nullptr(rffi.CCHARP.TO)

    def __init__(self, space, cdata, ctype):
        from pypy.module._cffi_backend import ctypeprim
        assert lltype.typeOf(cdata) == rffi.CCHARP
        assert isinstance(ctype, ctypeprim.W_CType)
        self.space = space
        self._cdata = cdata    # don't forget keepalive_until_here!
        self.ctype = ctype

    def repr(self):
        extra = self.ctype.extra_repr(self._cdata)
        keepalive_until_here(self)
        return self.space.wrap("<cdata '%s' %s>" % (self.ctype.name, extra))

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
        from pypy.module._cffi_backend import ctypearray
        space = self.space
        if isinstance(self.ctype, ctypearray.W_CTypeArray):
            return space.wrap(self.get_array_length())
        raise operationerrfmt(space.w_TypeError,
                              "cdata of type '%s' has no len()",
                              self.ctype.name)

    def str(self):
        return self.ctype.str(self)

    def _cmp(self, w_other, compare_for_ne):
        space = self.space
        cdata1 = self._cdata
        other = space.interpclass_w(w_other)
        if isinstance(other, W_CData):
            cdata2 = other._cdata
        else:
            return space.w_NotImplemented
        result = (cdata1 == cdata2) ^ compare_for_ne
        return space.newbool(result)

    def eq(self, w_other): return self._cmp(w_other, False)
    def ne(self, w_other): return self._cmp(w_other, True)

    def hash(self):
        h = (objectmodel.compute_identity_hash(self.ctype) ^
             rffi.cast(lltype.Signed, self._cdata))
        return self.space.wrap(h)

    def getitem(self, w_index):
        space = self.space
        i = space.getindex_w(w_index, space.w_IndexError)
        self.ctype._check_subscript_index(self, i)
        w_o = self._do_getitem(i)
        keepalive_until_here(self)
        return w_o

    def _do_getitem(self, i):
        ctitem = self.ctype.ctitem
        return ctitem.convert_to_object(
            rffi.ptradd(self._cdata, i * ctitem.size))

    def setitem(self, w_index, w_value):
        space = self.space
        i = space.getindex_w(w_index, space.w_IndexError)
        self.ctype._check_subscript_index(self, i)
        ctitem = self.ctype.ctitem
        ctitem.convert_from_object(
            rffi.ptradd(self._cdata, i * ctitem.size),
            w_value)
        keepalive_until_here(self)

    def _add_or_sub(self, w_other, sign):
        space = self.space
        i = sign * space.getindex_w(w_other, space.w_OverflowError)
        return self.ctype.add(self._cdata, i)

    def add(self, w_other):
        return self._add_or_sub(w_other, +1)

    def sub(self, w_other):
        space = self.space
        ob = space.interpclass_w(w_other)
        if isinstance(ob, W_CData):
            from pypy.module._cffi_backend import ctypeptr, ctypearray
            ct = ob.ctype
            if isinstance(ct, ctypearray.W_CTypeArray):
                ct = ct.ctptr
            #
            if (ct is not self.ctype or
                   not isinstance(ct, ctypeptr.W_CTypePointer) or
                   ct.ctitem.size <= 0):
                raise operationerrfmt(space.w_TypeError,
                    "cannot subtract cdata '%s' and cdata '%s'",
                    self.ctype.name, ct.name)
            #
            diff = (rffi.cast(lltype.Signed, self._cdata) -
                    rffi.cast(lltype.Signed, ob._cdata)) // ct.ctitem.size
            return space.wrap(diff)
        #
        return self._add_or_sub(w_other, -1)

    def getcfield(self, w_attr):
        from pypy.module._cffi_backend import ctypeptr, ctypestruct
        space = self.space
        ctype = self.ctype
        attr = space.str_w(w_attr)
        if isinstance(ctype, ctypeptr.W_CTypePointer):
            ctype = ctype.ctitem
        if (isinstance(ctype, ctypestruct.W_CTypeStructOrUnion) and
                ctype.fields_dict is not None):
            try:
                return ctype.fields_dict[attr]
            except KeyError:
                pass
        raise operationerrfmt(space.w_AttributeError,
                              "cdata '%s' has no attribute '%s'",
                              ctype.name, attr)

    def getattr(self, w_attr):
        w_res = self.getcfield(w_attr).read(self._cdata)
        keepalive_until_here(self)
        return w_res

    def setattr(self, w_attr, w_value):
        self.getcfield(w_attr).write(self._cdata, w_value)
        keepalive_until_here(self)

    def call(self, args_w):
        w_result = self.ctype.call(self._cdata, args_w)
        keepalive_until_here(self)
        return w_result

    def write_raw_integer_data(self, source):
        misc.write_raw_integer_data(self._cdata, source, self.ctype.size)
        keepalive_until_here(self)

    def write_raw_float_data(self, source):
        misc.write_raw_float_data(self._cdata, source, self.ctype.size)
        keepalive_until_here(self)

    def convert_to_object(self):
        w_obj = self.ctype.convert_to_object(self._cdata)
        keepalive_until_here(self)
        return w_obj

    def get_array_length(self):
        from pypy.module._cffi_backend import ctypearray
        ctype = self.ctype
        assert isinstance(ctype, ctypearray.W_CTypeArray)
        length = ctype.length
        assert length >= 0
        return length


class W_CDataApplevelOwning(W_CData):
    """This is the abstract base class for classes that are of the app-level
    type '_cffi_backend.CDataOwn'.  These are weakrefable."""
    _attrs_ = ['_lifeline_']    # for weakrefs
    _immutable_ = True

    def _owning_num_bytes(self):
        return self.ctype.size

    def repr(self):
        return self.space.wrap("<cdata '%s' owning %d bytes>" % (
            self.ctype.name, self._owning_num_bytes()))


class W_CDataNewOwning(W_CDataApplevelOwning):
    """This is the class used for the app-level type
    '_cffi_backend.CDataOwn' created by newp()."""
    _attrs_ = []
    _immutable_ = True

    def __init__(self, space, size, ctype):
        cdata = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw', zero=True)
        W_CDataApplevelOwning.__init__(self, space, cdata, ctype)

    @rgc.must_be_light_finalizer
    def __del__(self):
        lltype.free(self._cdata, flavor='raw')


class W_CDataNewOwningLength(W_CDataNewOwning):
    """Subclass with an explicit length, for allocated instances of
    the C type 'foo[]'."""
    _attrs_ = ['length']
    _immutable_ = True

    def __init__(self, space, size, ctype, length):
        W_CDataNewOwning.__init__(self, space, size, ctype)
        self.length = length

    def _owning_num_bytes(self):
        from pypy.module._cffi_backend import ctypearray
        ctype = self.ctype
        assert isinstance(ctype, ctypearray.W_CTypeArray)
        return self.length * ctype.ctitem.size

    def get_array_length(self):
        return self.length


class W_CDataPtrToStructOrUnion(W_CDataApplevelOwning):
    """This subclass is used for the pointer returned by new('struct foo').
    It has a strong reference to a W_CDataNewOwning that really owns the
    struct, which is the object returned by the app-level expression 'p[0]'."""
    _attrs_ = ['structobj']
    _immutable_ = True

    def __init__(self, space, cdata, ctype, structobj):
        W_CDataApplevelOwning.__init__(self, space, cdata, ctype)
        self.structobj = structobj

    def _owning_num_bytes(self):
        from pypy.module._cffi_backend.ctypeptr import W_CTypePtrBase
        ctype = self.ctype
        assert isinstance(ctype, W_CTypePtrBase)
        return ctype.ctitem.size

    def _do_getitem(self, i):
        return self.structobj


class W_CDataCasted(W_CData):
    """This subclass is used by the results of cffi.cast('int', x)
    or other primitive explicitly-casted types.  Relies on malloc'ing
    small bits of memory (e.g. just an 'int').  Its point is to not be
    a subclass of W_CDataApplevelOwning."""
    _attrs_ = []
    _immutable_ = True

    def __init__(self, space, size, ctype):
        cdata = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw', zero=True)
        W_CData.__init__(self, space, cdata, ctype)

    @rgc.must_be_light_finalizer
    def __del__(self):
        lltype.free(self._cdata, flavor='raw')


W_CData.typedef = TypeDef(
    '_cffi_backend.CData',
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
    __add__ = interp2app(W_CData.add),
    __sub__ = interp2app(W_CData.sub),
    __getattr__ = interp2app(W_CData.getattr),
    __setattr__ = interp2app(W_CData.setattr),
    __call__ = interp2app(W_CData.call),
    )
W_CData.typedef.acceptable_as_base_class = False

W_CDataApplevelOwning.typedef = TypeDef(
    '_cffi_backend.CDataOwn',
    W_CData.typedef,    # base typedef
    __repr__ = interp2app(W_CDataApplevelOwning.repr),
    __weakref__ = make_weakref_descr(W_CDataApplevelOwning),
    )
W_CDataApplevelOwning.typedef.acceptable_as_base_class = False
