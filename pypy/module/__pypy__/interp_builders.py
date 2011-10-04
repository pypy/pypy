from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rlib.rstring import UnicodeBuilder, StringBuilder
from pypy.tool.sourcetools import func_with_new_name


def create_builder(name, strtype, builder_cls):
    class W_Builder(Wrappable):
        def __init__(self, space, size):
            if size < 0:
                self.builder = builder_cls()
            else:
                self.builder = builder_cls(size)

        def _check_done(self, space):
            if self.builder is None:
                raise OperationError(space.w_ValueError, space.wrap("Can't operate on a done builder"))

        @unwrap_spec(size=int)
        def descr__new__(space, w_subtype, size=-1):
            return W_Builder(space, size)

        @unwrap_spec(s=strtype)
        def descr_append(self, space, s):
            self._check_done(space)
            self.builder.append(s)

        @unwrap_spec(s=strtype, start=int, end=int)
        def descr_append_slice(self, space, s, start, end):
            self._check_done(space)
            if not 0 <= start <= end <= len(s):
                raise OperationError(space.w_ValueError, space.wrap("bad start/stop"))
            self.builder.append_slice(s, start, end)

        def descr_build(self, space):
            self._check_done(space)
            w_s = space.wrap(self.builder.build())
            self.builder = None
            return w_s

        def descr_len(self, space):
            if self.builder is None:
                raise OperationError(space.w_ValueError,
                                     space.wrap('no lenght of built builder'))
            return space.wrap(self.builder.getlength())

    W_Builder.__name__ = "W_%s" % name
    W_Builder.typedef = TypeDef(name,
        __new__ = interp2app(func_with_new_name(
                                    W_Builder.descr__new__.im_func,
                                    '%s_new' % (name,))),
        append = interp2app(W_Builder.descr_append),
        append_slice = interp2app(W_Builder.descr_append_slice),
        build = interp2app(W_Builder.descr_build),
        __len__ = interp2app(W_Builder.descr_len),
    )
    W_Builder.typedef.acceptable_as_base_class = False
    return W_Builder

W_StringBuilder = create_builder("StringBuilder", str, StringBuilder)
W_UnicodeBuilder = create_builder("UnicodeBuilder", unicode, UnicodeBuilder)
