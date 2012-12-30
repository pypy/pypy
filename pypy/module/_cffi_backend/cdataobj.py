import operator
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.objectmodel import keepalive_until_here, specialize
from rpython.rlib import objectmodel, rgc
from pypy.tool.sourcetools import func_with_new_name

from pypy.module._cffi_backend import misc


class W_CData(Wrappable):
    _attrs_ = ['space', '_cdata', 'ctype', '_lifeline_']
    _immutable_fields_ = ['_cdata', 'ctype']
    _cdata = lltype.nullptr(rffi.CCHARP.TO)

    def __init__(self, space, cdata, ctype):
        from pypy.module._cffi_backend import ctypeprim
        assert lltype.typeOf(cdata) == rffi.CCHARP
        assert isinstance(ctype, ctypeprim.W_CType)
        self.space = space
        self._cdata = cdata    # don't forget keepalive_until_here!
        self.ctype = ctype

    def _repr_extra(self):
        extra = self.ctype.extra_repr(self._cdata)
        keepalive_until_here(self)
        return extra

    def _repr_extra_owning(self):
        from pypy.module._cffi_backend.ctypeptr import W_CTypePointer
        ctype = self.ctype
        if isinstance(ctype, W_CTypePointer):
            num_bytes = ctype.ctitem.size
        else:
            num_bytes = self._sizeof()
        return 'owning %d bytes' % num_bytes

    def repr(self):
        extra2 = self._repr_extra()
        extra1 = ''
        if not isinstance(self, W_CDataNewOwning):
            # it's slightly confusing to get "<cdata 'struct foo' 0x...>"
            # because the struct foo is not owned.  Trying to make it
            # clearer, write in this case "<cdata 'struct foo &' 0x...>".
            from pypy.module._cffi_backend import ctypestruct
            if isinstance(self.ctype, ctypestruct.W_CTypeStructOrUnion):
                extra1 = ' &'
        return self.space.wrap("<cdata '%s%s' %s>" % (
            self.ctype.name, extra1, extra2))

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

    def _make_comparison(name):
        op = getattr(operator, name)
        requires_ordering = name not in ('eq', 'ne')
        #
        def _cmp(self, w_other):
            from pypy.module._cffi_backend.ctypeprim import W_CTypePrimitive
            space = self.space
            cdata1 = self._cdata
            other = space.interpclass_w(w_other)
            if isinstance(other, W_CData):
                cdata2 = other._cdata
            else:
                return space.w_NotImplemented

            if requires_ordering:
                if (isinstance(self.ctype, W_CTypePrimitive) or
                    isinstance(other.ctype, W_CTypePrimitive)):
                    raise OperationError(space.w_TypeError,
                        space.wrap("cannot do comparison on a primitive cdata"))
                cdata1 = rffi.cast(lltype.Unsigned, cdata1)
                cdata2 = rffi.cast(lltype.Unsigned, cdata2)
            return space.newbool(op(cdata1, cdata2))
        #
        return func_with_new_name(_cmp, name)

    lt = _make_comparison('lt')
    le = _make_comparison('le')
    eq = _make_comparison('eq')
    ne = _make_comparison('ne')
    gt = _make_comparison('gt')
    ge = _make_comparison('ge')

    def hash(self):
        h = (objectmodel.compute_identity_hash(self.ctype) ^
             rffi.cast(lltype.Signed, self._cdata))
        return self.space.wrap(h)

    def getitem(self, w_index):
        space = self.space
        i = space.getindex_w(w_index, space.w_IndexError)
        ctype = self.ctype._check_subscript_index(self, i)
        w_o = self._do_getitem(ctype, i)
        keepalive_until_here(self)
        return w_o

    def _do_getitem(self, ctype, i):
        ctitem = ctype.ctitem
        return ctitem.convert_to_object(
            rffi.ptradd(self._cdata, i * ctitem.size))

    def setitem(self, w_index, w_value):
        space = self.space
        i = space.getindex_w(w_index, space.w_IndexError)
        ctype = self.ctype._check_subscript_index(self, i)
        ctitem = ctype.ctitem
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
        return self.ctype.getcfield(self.space.str_w(w_attr))

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

    def iter(self):
        return self.ctype.iter(self)

    @specialize.argtype(1)
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

    def _sizeof(self):
        return self.ctype.size


class W_CDataMem(W_CData):
    """This is the base class used for cdata objects that own and free
    their memory.  Used directly by the results of cffi.cast('int', x)
    or other primitive explicitly-casted types.  It is further subclassed
    by W_CDataNewOwning."""
    _attrs_ = []

    def __init__(self, space, size, ctype):
        cdata = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw', zero=True)
        W_CData.__init__(self, space, cdata, ctype)

    @rgc.must_be_light_finalizer
    def __del__(self):
        lltype.free(self._cdata, flavor='raw')


class W_CDataNewOwning(W_CDataMem):
    """This is the class used for the cata objects created by newp()."""
    _attrs_ = []

    def _repr_extra(self):
        return self._repr_extra_owning()


class W_CDataNewOwningLength(W_CDataNewOwning):
    """Subclass with an explicit length, for allocated instances of
    the C type 'foo[]'."""
    _attrs_ = ['length']
    _immutable_fields_ = ['length']

    def __init__(self, space, size, ctype, length):
        W_CDataNewOwning.__init__(self, space, size, ctype)
        self.length = length

    def _sizeof(self):
        from pypy.module._cffi_backend import ctypearray
        ctype = self.ctype
        assert isinstance(ctype, ctypearray.W_CTypeArray)
        return self.length * ctype.ctitem.size

    def get_array_length(self):
        return self.length


class W_CDataPtrToStructOrUnion(W_CData):
    """This subclass is used for the pointer returned by new('struct foo').
    It has a strong reference to a W_CDataNewOwning that really owns the
    struct, which is the object returned by the app-level expression 'p[0]'.
    But it is not itself owning any memory, although its repr says so;
    it is merely a co-owner."""
    _attrs_ = ['structobj']
    _immutable_fields_ = ['structobj']

    def __init__(self, space, cdata, ctype, structobj):
        W_CData.__init__(self, space, cdata, ctype)
        self.structobj = structobj

    def _repr_extra(self):
        return self._repr_extra_owning()

    def _do_getitem(self, ctype, i):
        assert i == 0
        return self.structobj


W_CData.typedef = TypeDef(
    'CData',
    __module__ = '_cffi_backend',
    __repr__ = interp2app(W_CData.repr),
    __nonzero__ = interp2app(W_CData.nonzero),
    __int__ = interp2app(W_CData.int),
    __long__ = interp2app(W_CData.long),
    __float__ = interp2app(W_CData.float),
    __len__ = interp2app(W_CData.len),
    __lt__ = interp2app(W_CData.lt),
    __le__ = interp2app(W_CData.le),
    __eq__ = interp2app(W_CData.eq),
    __ne__ = interp2app(W_CData.ne),
    __gt__ = interp2app(W_CData.gt),
    __ge__ = interp2app(W_CData.ge),
    __hash__ = interp2app(W_CData.hash),
    __getitem__ = interp2app(W_CData.getitem),
    __setitem__ = interp2app(W_CData.setitem),
    __add__ = interp2app(W_CData.add),
    __sub__ = interp2app(W_CData.sub),
    __getattr__ = interp2app(W_CData.getattr),
    __setattr__ = interp2app(W_CData.setattr),
    __call__ = interp2app(W_CData.call),
    __iter__ = interp2app(W_CData.iter),
    __weakref__ = make_weakref_descr(W_CData),
    )
W_CData.typedef.acceptable_as_base_class = False
