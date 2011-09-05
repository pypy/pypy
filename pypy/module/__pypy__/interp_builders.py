from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rlib.rstring import UnicodeBuilder


class W_UnicodeBuilder(Wrappable):
    def __init__(self, space, size):
        if size < 0:
            self.builder = UnicodeBuilder()
        else:
            self.builder = UnicodeBuilder(size)
        self.done = False

    def _check_done(self, space):
        if self.done:
            raise OperationError(space.w_ValueError, space.wrap("Can't operate on a done builder"))

    @unwrap_spec(size=int)
    def descr__new__(space, w_subtype, size=-1):
        return W_UnicodeBuilder(space, size)

    @unwrap_spec(s=unicode)
    def descr_append(self, space, s):
        self._check_done(space)
        self.builder.append(s)

    @unwrap_spec(s=unicode, start=int, end=int)
    def descr_append_slice(self, space, s, start, end):
        self._check_done(space)
        if not 0 <= start <= end <= len(s):
            raise OperationError(space.w_ValueError, space.wrap("bad start/stop"))
        self.builder.append_slice(s, start, end)

    def descr_build(self, space):
        self._check_done(space)
        w_s = space.wrap(self.builder.build())
        self.done = True
        return w_s


W_UnicodeBuilder.typedef = TypeDef("UnicodeBuilder",
    __new__ = interp2app(W_UnicodeBuilder.descr__new__.im_func),

    append = interp2app(W_UnicodeBuilder.descr_append),
    append_slice = interp2app(W_UnicodeBuilder.descr_append_slice),
    build = interp2app(W_UnicodeBuilder.descr_build),
)
W_UnicodeBuilder.typedef.acceptable_as_base_class = False
