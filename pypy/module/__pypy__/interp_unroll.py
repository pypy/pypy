from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef


class W_LoopUnroller(W_Root):
    def __init__(self, w_obj):
        self.w_obj = w_obj

    def descr__new__(space, w_subtype, w_obj):
        return W_LoopUnroller(w_obj)

    def descr__repr__(self, space):
        return space.wrap("LoopUnroller(%s)" % space.str_w(space.repr(self.w_obj)))

    def descr__iter__(self, space):
        return space.iter(self.w_obj)


W_LoopUnroller.typedef = TypeDef("LoopUnroller",
    __new__=interp2app(W_LoopUnroller.descr__new__.im_func),
    __repr__=interp2app(W_LoopUnroller.descr__repr__),
    __iter__=interp2app(W_LoopUnroller.descr__iter__),
)
