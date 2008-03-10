from pypy.rlib import rsha
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root


class W_SHA(Wrappable, rsha.RSHA):
    """
    A subclass of RSHA that can be exposed to app-level.
    """

    def __init__(self, space):
        self.space = space
        self._init()

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
    __new__   = interp2app(W_SHA___new__, unwrap_spec=[ObjSpace, W_Root,
                                                       'bufferstr']),
    update    = interp2app(W_SHA.update_w, unwrap_spec=['self', 'bufferstr']),
    digest    = interp2app(W_SHA.digest_w, unwrap_spec=['self']),
    hexdigest = interp2app(W_SHA.hexdigest_w, unwrap_spec=['self']),
    copy      = interp2app(W_SHA.copy_w, unwrap_spec=['self']),
    __doc__   = """sha(arg) -> return new sha object.

If arg is present, the method call update(arg) is made.""")
