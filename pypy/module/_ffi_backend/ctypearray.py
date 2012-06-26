"""
Arrays.
"""

from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.rpython.lltypesystem import rffi
from pypy.rlib.objectmodel import keepalive_until_here
from pypy.rlib.rarithmetic import ovfcheck

from pypy.module._ffi_backend.ctypeobj import W_CType
from pypy.module._ffi_backend.ctypeprim import W_CTypePrimitiveChar
from pypy.module._ffi_backend.ctypeptr import W_CTypePtrOrArray
from pypy.module._ffi_backend import cdataobj


class W_CTypeArray(W_CTypePtrOrArray):

    def __init__(self, space, ctptr, length, arraysize, extra):
        W_CTypePtrOrArray.__init__(self, space, arraysize, extra, 0,
                                   ctptr.ctitem)
        self.length = length
        self.ctptr = ctptr

    def str(self, cdataobj):
        if isinstance(self.ctitem, W_CTypePrimitiveChar):
            s = rffi.charp2strn(cdataobj._cdata, cdataobj.get_array_length())
            keepalive_until_here(cdataobj)
            return self.space.wrap(s)
        return W_CTypePtrOrArray.str(self, cdataobj)

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
            elif space.isinstance_w(w_init, space.w_str):
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
            cdata = cdataobj.W_CDataOwnLength(space, datasize, self, length)
        #
        else:
            cdata = cdataobj.W_CDataOwn(space, datasize, self)
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

    def convert_from_object(self, cdata, w_ob):
        space = self.space
        if (space.isinstance_w(w_ob, space.w_list) or
            space.isinstance_w(w_ob, space.w_tuple)):
            lst_w = space.listview(w_ob)
            if self.length >= 0 and len(lst_w) > self.length:
                raise operationerrfmt(space.w_IndexError,
                    "too many initializers for '%s' (got %d)",
                                      self.name, len(lst_w))
            ctitem = self.ctitem
            for i in range(len(lst_w)):
                ctitem.convert_from_object(cdata, lst_w[i])
                cdata = rffi.ptradd(cdata, ctitem.size)
        elif isinstance(self.ctitem, W_CTypePrimitiveChar):
            try:
                s = space.str_w(w_ob)
            except OperationError, e:
                if not e.match(space, space.w_TypeError):
                    raise
                raise self._convert_error("str or list or tuple", w_ob)
            n = len(s)
            if self.length >= 0 and n > self.length:
                raise operationerrfmt(space.w_IndexError,
                                      "initializer string is too long for '%s'"
                                      " (got %d characters)",
                                      self.name, n)
            for i in range(n):
                cdata[i] = s[i]
            if n != self.length:
                cdata[n] = '\x00'
        else:
            raise self._convert_error("list or tuple", w_ob)

    def convert_to_object(self, cdata):
        return cdataobj.W_CData(self.space, cdata, self)

    def add(self, cdata, i):
        p = rffi.ptradd(cdata, i * self.ctitem.size)
        return cdataobj.W_CData(self.space, p, self.ctptr)
