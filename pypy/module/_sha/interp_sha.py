from pypy.rlib import rsha
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec


class W_SHA(Wrappable, rsha.RSHA):
    """
    A subclass of RSHA that can be exposed to app-level.
    """

    def __init__(self, space):
        self.space = space
        self._init()

    @unwrap_spec(string='bufferstr')
    def update_w(self, string):
        self.update(string)

    def digest_w(self):
        return self.space.wrap(self.digest())

    def hexdigest_w(self):
        return self.space.wrap(self.hexdigest())

    def copy_w(self):
        clone = W_SHA(self.space)
        clone._copyfrom(self)
        return self.space.wrap(clone)


@unwrap_spec(initialdata='bufferstr')
def W_SHA___new__(space, w_subtype, initialdata=''):
    """
    Create a new sha object and call its initializer.
    """
    w_sha = space.allocate_instance(W_SHA, w_subtype)
    sha = space.interp_w(W_SHA, w_sha)
    W_SHA.__init__(sha, space)
    sha.update(initialdata)
    return w_sha


W_SHA.typedef = TypeDef(
    'SHAType',
    __new__   = interp2app(W_SHA___new__),
    update    = interp2app(W_SHA.update_w),
    digest    = interp2app(W_SHA.digest_w),
    hexdigest = interp2app(W_SHA.hexdigest_w),
    copy      = interp2app(W_SHA.copy_w),
    digest_size = 20,
    digestsize = 20,
    block_size = 64,
    __doc__   = """sha(arg) -> return new sha object.

If arg is present, the method call update(arg) is made.""")
