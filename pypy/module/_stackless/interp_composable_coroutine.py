from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, interp2app
from pypy.module._stackless.interp_coroutine import AppCoState, AppCoroutine


class W_UserCoState(Wrappable):
    def __init__(self, space):
        self.costate = AppCoState(space)
        self.costate.post_install()

    def descr_method__new__(space, w_subtype):
        costate = space.allocate_instance(W_UserCoState, w_subtype)
        W_UserCoState.__init__(costate, space)
        return space.wrap(costate)

    def w_getcurrent(self):
        space = self.costate.space
        return space.wrap(self.costate.current)

    def w_spawn(self, w_subtype=None):
        space = self.costate.space
        if space.is_w(w_subtype, space.w_None):
            w_subtype = space.gettypeobject(AppCoroutine.typedef)
        co = space.allocate_instance(AppCoroutine, w_subtype)
        AppCoroutine.__init__(co, space, state=self.costate)
        return space.wrap(co)

W_UserCoState.typedef = TypeDef("usercostate",
    __new__ = interp2app(W_UserCoState.descr_method__new__.im_func),
    __module__ = '_stackless',
    getcurrent = interp2app(W_UserCoState.w_getcurrent),
    spawn      = interp2app(W_UserCoState.w_spawn),
)
