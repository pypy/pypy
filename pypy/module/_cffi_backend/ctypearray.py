"""
Arrays.
"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef

from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rlib.rarithmetic import ovfcheck

from pypy.module._cffi_backend import cdataobj
from pypy.module._cffi_backend.ctypeptr import W_CTypePtrOrArray


class W_CTypeArray(W_CTypePtrOrArray):
    _attrs_            = ['ctptr']
    _immutable_fields_ = ['ctptr']
    kind = "array"

    def __init__(self, space, ctptr, length, arraysize, extra):
        W_CTypePtrOrArray.__init__(self, space, arraysize, extra, 0,
                                   ctptr.ctitem)
        self.length = length
        self.ctptr = ctptr

    def _alignof(self):
        return self.ctitem.alignof()

    def newp(self, w_init):
        space = self.space
        datasize = self.size
        #
        if datasize < 0:
            if (space.isinstance_w(w_init, space.w_list) or
                space.isinstance_w(w_init, space.w_tuple)):
                length = space.int_w(space.len(w_init))
            elif space.isinstance_w(w_init, space.w_basestring):
                # from a string, we add the null terminator
                length = space.int_w(space.len(w_init)) + 1
            else:
                length = space.getindex_w(w_init, space.w_OverflowError)
                if length < 0:
                    raise OperationError(space.w_ValueError,
                                         space.wrap("negative array length"))
                w_init = space.w_None
            #
            try:
                datasize = ovfcheck(length * self.ctitem.size)
            except OverflowError:
                raise OperationError(space.w_OverflowError,
                    space.wrap("array size would overflow a ssize_t"))
            #
            cdata = cdataobj.W_CDataNewOwningLength(space, datasize,
                                                    self, length)
        #
        else:
            cdata = cdataobj.W_CDataNewOwning(space, datasize, self)
        #
        if not space.is_w(w_init, space.w_None):
            self.convert_from_object(cdata._cdata, w_init)
            keepalive_until_here(cdata)
        return cdata

    def _check_subscript_index(self, w_cdata, i):
        space = self.space
        if i < 0:
            raise OperationError(space.w_IndexError,
                                 space.wrap("negative index not supported"))
        if i >= w_cdata.get_array_length():
            raise operationerrfmt(space.w_IndexError,
                "index too large for cdata '%s' (expected %d < %d)",
                self.name, i, w_cdata.get_array_length())
        return self

    def _check_slice_index(self, w_cdata, start, stop):
        space = self.space
        if start < 0:
            raise OperationError(space.w_IndexError,
                                 space.wrap("negative index not supported"))
        if stop > w_cdata.get_array_length():
            raise operationerrfmt(space.w_IndexError,
                "index too large (expected %d <= %d)",
                stop, w_cdata.get_array_length())
        return self.ctptr

    def convert_from_object(self, cdata, w_ob):
        self.convert_array_from_object(cdata, w_ob)

    def convert_to_object(self, cdata):
        if self.length < 0:
            # we can't return a <cdata 'int[]'> here, because we don't
            # know the length to give it.  As a compromize, returns
            # <cdata 'int *'> in this case.
            self = self.ctptr
        #
        return cdataobj.W_CData(self.space, cdata, self)

    def add(self, cdata, i):
        p = rffi.ptradd(cdata, i * self.ctitem.size)
        return cdataobj.W_CData(self.space, p, self.ctptr)

    def iter(self, cdata):
        return W_CDataIter(self.space, self.ctitem, cdata)

    def get_vararg_type(self):
        return self.ctptr

    def _fget(self, attrchar):
        if attrchar == 'i':     # item
            return self.space.wrap(self.ctitem)
        if attrchar == 'l':     # length
            if self.length >= 0:
                return self.space.wrap(self.length)
            else:
                return self.space.w_None
        return W_CTypePtrOrArray._fget(self, attrchar)


class W_CDataIter(W_Root):
    _immutable_fields_ = ['ctitem', 'cdata', '_stop']    # but not '_next'

    def __init__(self, space, ctitem, cdata):
        self.space = space
        self.ctitem = ctitem
        self.cdata = cdata
        length = cdata.get_array_length()
        self._next = cdata._cdata
        self._stop = rffi.ptradd(cdata._cdata, length * ctitem.size)

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        result = self._next
        if result == self._stop:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        self._next = rffi.ptradd(result, self.ctitem.size)
        return self.ctitem.convert_to_object(result)

W_CDataIter.typedef = TypeDef(
    'CDataIter',
    __module__ = '_cffi_backend',
    __iter__ = interp2app(W_CDataIter.iter_w),
    next = interp2app(W_CDataIter.next_w),
    )
W_CDataIter.typedef.acceptable_as_base_class = False
