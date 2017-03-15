import inspect

import py

from pypy.objspace.std.bytesobject import (W_AbstractBytesObject,
    W_BytesObject, StringBuffer)
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError
from rpython.rlib.rstring import StringBuilder


class W_StringBufferObject(W_AbstractBytesObject):
    w_str = None

    def __init__(self, builder):
        self.builder = builder             # StringBuilder
        self.length = builder.getlength()

    def force(self):
        if self.w_str is None:
            s = self.builder.build()
            if self.length < len(s):
                s = s[:self.length]
            self.w_str = W_BytesObject(s)
            return s
        else:
            return self.w_str._value

    def __repr__(self):
        """ representation for debugging purposes """
        return "%s(%r[:%d])" % (
            self.__class__.__name__, self.builder, self.length)

    def unwrap(self, space):
        return self.force()

    def bytes_w(self, space):
        return self.force()

    def buffer_w(self, space, flags):
        return StringBuffer(self.force())

    def descr_len(self, space):
        return space.newint(self.length)

    def descr_add(self, space, w_other):
        try:
            other = W_BytesObject._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        if self.builder.getlength() != self.length:
            builder = StringBuilder()
            builder.append(self.force())
        else:
            builder = self.builder
        builder.append(other)
        return W_StringBufferObject(builder)

    def descr_str(self, space):
        # you cannot get subclasses of W_StringBufferObject here
        assert type(self) is W_StringBufferObject
        return self


delegation_dict = {}
for key, value in W_BytesObject.typedef.rawdict.iteritems():
    if not isinstance(value, interp2app):
        continue
    if key in ('__len__', '__add__', '__str__'):
        continue

    func = value._code._bltin
    args = inspect.getargs(func.func_code)
    if args.varargs or args.keywords:
        raise TypeError("Varargs and keywords not supported in unwrap_spec")
    argspec = ', '.join([arg for arg in args.args[1:]])
    func_code = py.code.Source("""
    def f(self, %(args)s):
        self.force()
        return self.w_str.%(func_name)s(%(args)s)
    """ % {'args': argspec, 'func_name': func.func_name})
    d = {}
    exec func_code.compile() in d
    f = d['f']
    f.func_defaults = func.func_defaults
    f.__module__ = func.__module__
    # necessary for unique identifiers for pickling
    f.func_name = func.func_name
    unwrap_spec_ = getattr(func, 'unwrap_spec', None)
    if unwrap_spec_ is not None:
        f = unwrap_spec(**unwrap_spec_)(f)
    setattr(W_StringBufferObject, func.func_name, f)

W_StringBufferObject.typedef = W_BytesObject.typedef
