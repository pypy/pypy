from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.module._stackless.interp_coroutine import AppCoroutine, AppCoState
from pypy.module._stackless.interp_coroutine import makeStaticMethod
from pypy.rlib.rcoroutine import AbstractThunk
from pypy.module._stackless.rclonable import InterpClonableMixin


class AppClonableCoroutine(AppCoroutine, InterpClonableMixin):

    def newsubctx(self):
        self.hello_local_pool()
        AppCoroutine.newsubctx(self)
        self.goodbye_local_pool()

    def hello(self):
        self.hello_local_pool()
        AppCoroutine.hello(self)

    def goodbye(self):
        AppCoroutine.goodbye(self)
        self.goodbye_local_pool()

    def descr_method__new__(space, w_subtype):
        co = space.allocate_instance(AppClonableCoroutine, w_subtype)
        costate = AppClonableCoroutine._get_state(space)
        AppClonableCoroutine.__init__(co, space, state=costate)
        return space.wrap(co)

    def _get_state(space):
        return space.fromcache(AppClonableCoState)
    _get_state = staticmethod(_get_state)

    def w_getcurrent(space):
        return space.wrap(AppClonableCoroutine._get_state(space).current)
    w_getcurrent = staticmethod(w_getcurrent)

    def w_clone(self):
        space = self.space
        costate = self.costate
        if costate.current is self:
            raise OperationError(space.w_RuntimeError,
                                 space.wrap("clone() cannot clone the "
                                            "current coroutine"
                                            "; use fork() instead"))
        copy = AppClonableCoroutine(space, state=costate)
        copy.subctx = self.clone_into(copy, self.subctx)
        return space.wrap(copy)

    def descr__reduce__(self, space):
        raise OperationError(space.w_TypeError,
                             space.wrap("_stackless.clonable instances are "
                                        "not picklable"))


AppClonableCoroutine.typedef = TypeDef("clonable", AppCoroutine.typedef,
    __new__    = interp2app(AppClonableCoroutine.descr_method__new__.im_func),
    getcurrent = interp2app(AppClonableCoroutine.w_getcurrent),
    clone      = interp2app(AppClonableCoroutine.w_clone),
    __reduce__ = interp2app(AppClonableCoroutine.descr__reduce__,
                            unwrap_spec=['self', ObjSpace]),
)

class AppClonableCoState(AppCoState):
    def post_install(self):
        self.current = self.main = AppClonableCoroutine(self.space, state=self)
        self.main.subctx.framestack = None      # wack

def post_install(module):
    makeStaticMethod(module, 'clonable', 'getcurrent')
    space = module.space
    AppClonableCoroutine._get_state(space).post_install()

# ____________________________________________________________

class ForkThunk(AbstractThunk):
    def __init__(self, coroutine):
        self.coroutine = coroutine
        self.newcoroutine = None
    def call(self):
        oldcoro = self.coroutine
        self.coroutine = None
        newcoro = AppClonableCoroutine(oldcoro.space, state=oldcoro.costate)
        newcoro.subctx = oldcoro.clone_into(newcoro, oldcoro.subctx)
        newcoro.parent = oldcoro
        self.newcoroutine = newcoro

def fork(space):
    """Fork, as in the Unix fork(): the call returns twice, and the return
    value of the call is either the new 'child' coroutine object (if returning
    into the parent), or None (if returning into the child).  This returns
    into the parent first, which can switch to the child later.
    """
    costate = AppClonableCoroutine._get_state(space)
    current = costate.current
    if current is costate.main:
        raise OperationError(space.w_RuntimeError,
                             space.wrap("cannot fork() in the main "
                                        "clonable coroutine"))
    thunk = ForkThunk(current)
    coro_fork = AppClonableCoroutine(space, state=costate)
    coro_fork.bind(thunk)
    coro_fork.switch()
    # we resume here twice.  The following would need explanations about
    # why it returns the correct thing in both the parent and the child...
    return space.wrap(thunk.newcoroutine)
fork.unwrap_spec = [ObjSpace]
