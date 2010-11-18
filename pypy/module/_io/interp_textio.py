from pypy.module._io.interp_iobase import W_IOBase
from pypy.interpreter.typedef import (
    TypeDef, GetSetProperty, interp_attrproperty_w, interp_attrproperty,
    generic_new_descr)
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError, operationerrfmt

class W_TextIOBase(W_IOBase):
    w_encoding = None

    def __init__(self, space):
        W_IOBase.__init__(self, space)

    def _unsupportedoperation(self, space, message):
        w_exc = space.getattr(space.getbuiltinmodule('_io'),
                              space.wrap('UnsupportedOperation'))
        raise OperationError(w_exc, space.wrap(message))

    @unwrap_spec('self', ObjSpace, W_Root)
    def read_w(self, space, w_size=None):
        self._unsupportedoperation(space, "read")

    @unwrap_spec('self', ObjSpace, W_Root)
    def readline_w(self, space, w_limit=None):
        self._unsupportedoperation(space, "readline")

W_TextIOBase.typedef = TypeDef(
    '_TextIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_TextIOBase),

    read = interp2app(W_TextIOBase.read_w),
    encoding = interp_attrproperty_w("w_encoding", W_TextIOBase)
    )

class W_TextIOWrapper(W_TextIOBase):
    @unwrap_spec('self', ObjSpace, W_Root, W_Root, W_Root, W_Root, int)
    def descr_init(self, space, w_buffer, w_encoding=None,
                   w_errors=None, w_newline=None, line_buffering=0):
        self.w_buffer = w_buffer
        self.w_encoding = w_encoding

        if space.is_w(w_newline, space.w_None):
            newline = None
        else:
            newline = space.str_w(w_newline)
        if newline and newline not in ('\n', '\r\n', '\r'):
            raise OperationError(space.w_ValueError, space.wrap(
                "illegal newline value: %s" % (newline,)))

        self.line_buffering = line_buffering

    @unwrap_spec('self', ObjSpace, W_Root)
    def read_w(self, space, w_size=None):
        # XXX w_size?
        w_bytes = space.call_method(self.w_buffer, "read")
        return space.call_method(w_bytes, "decode", self.w_encoding)

    @unwrap_spec('self', ObjSpace, W_Root)
    def readline_w(self, space, w_limit=None):
        # XXX w_limit?
        w_bytes = space.call_method(self.w_buffer, "readline")
        return space.call_method(w_bytes, "decode", self.w_encoding)

W_TextIOWrapper.typedef = TypeDef(
    'TextIOWrapper', W_TextIOBase.typedef,
    __new__ = generic_new_descr(W_TextIOWrapper),
    __init__  = interp2app(W_TextIOWrapper.descr_init),

    read = interp2app(W_TextIOWrapper.read_w),
    readline = interp2app(W_TextIOWrapper.readline_w),

    line_buffering = interp_attrproperty("line_buffering", W_TextIOWrapper),
    )
