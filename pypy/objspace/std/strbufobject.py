from pypy.objspace.std.bytesobject import W_AbstractBytesObject
from pypy.objspace.std.bytesobject import W_BytesObject
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

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r[:%d])" % (
            w_self.__class__.__name__, w_self.builder, w_self.length)

    def unwrap(self, space):
        return self.force()

    def str_w(self, space):
        return self.force()

    def descr_len(self, space):
        return space.wrap(self.length)

    def descr_add(self, space, w_other):
        if isinstance(w_other, W_AbstractBytesObject):
            other = w_other.str_w(space)
            if self.builder.getlength() != self.length:
                builder = StringBuilder()
                builder.append(self.force())
            else:
                builder = self.builder
            builder.append(other)
            return W_StringBufferObject(builder)
        else:
            self.force()
            return self.w_str.descr_add(space, w_other)

    def descr_str(self, space):
        # you cannot get subclasses of W_StringBufferObject here
        assert type(self) is W_StringBufferObject
        return self


def copy_from_base_class(baseclass, bufclass, attr_name):
    import inspect
    import py
    from pypy.interpreter.gateway import interp2app, unwrap_spec

    for key, value in baseclass.typedef.rawdict.iteritems():
        if not isinstance(value, interp2app):
            continue

        func = value._code._bltin
        if func.func_name in bufclass.__dict__:
            assert key in ('__len__', '__add__', '__str__', '__unicode__')
            continue

        args = inspect.getargs(func.func_code)
        if args.varargs or args.keywords:
            raise TypeError("Varargs and keywords not supported in unwrap_spec")
        argspec = ', '.join([arg for arg in args.args[1:]])
        func_code = py.code.Source("""
        def f(self, %(args)s):
            self.force()
            return self.%(attr_name)s.%(func_name)s(%(args)s)
        """ % {'args': argspec, 'func_name': func.func_name,
               'attr_name': attr_name})
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
        setattr(bufclass, func.func_name, f)

    bufclass.typedef = baseclass.typedef

copy_from_base_class(W_BytesObject, W_StringBufferObject, 'w_str')
