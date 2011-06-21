from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.rlib.rstring import UnicodeBuilder


class W_UnicodeBuilder(Wrappable):
    def __init__(self, space, size):
        if size == -1:
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
        if len(s) == 1:
            self.builder.append(s[0])
        else:
            self.builder.append(s)

    def descr_build(self, space):
        self._check_done(space)
        w_s = space.wrap(self.builder.build())
        self.done = True
        return w_s


W_UnicodeBuilder.typedef = TypeDef("UnicodeBuilder",
    __new__ = interp2app(W_UnicodeBuilder.descr__new__.im_func),

    append = interp2app(W_UnicodeBuilder.descr_append),
    build = interp2app(W_UnicodeBuilder.descr_build),
)
W_UnicodeBuilder.typedef.acceptable_as_base_class = False