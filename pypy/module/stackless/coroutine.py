"""
Coroutine implementation for application level on top
of the internal coroutines.
This is an extensible concept. Multiple implementations
of concurrency can exist together, if they follow the
basic concept of maintaining their own costate.

There is also some diversification possible by using
multiple costates for the same type. This leads to
disjoint switchable sets within the same type.

I'm not so sure to what extent the opposite is possible, too.
I.e., merging the costate of tasklets and greenlets would
allow them to be parents of each other. Needs a bit more
experience to decide where to set the limits.
"""

from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import StaticMethod

from pypy.module.stackless.stackless_flags import StacklessFlags
from pypy.module.stackless.interp_coroutine import Coroutine, BaseCoState, AbstractThunk

class _AppThunk(AbstractThunk):

    def __init__(self, space, costate, w_obj, args):
        self.space = space
        self.costate = costate
        if not space.is_true(space.callable(w_obj)):
            raise OperationError(
                space.w_TypeError, 
                space.mod(space.wrap('object %r is not callable'),
                          space.newtuple([w_obj])))
        self.w_func = w_obj
        self.args = args

    def call(self):
        self.costate.w_tempval = self.space.call_args(self.w_func, self.args)


class AppCoroutine(Coroutine): # XXX, StacklessFlags):

    def __init__(self, space, is_main=False):
        self.space = space
        state = self._get_state(space)
        Coroutine.__init__(self, state)
        self.flags = 0
        if not is_main:
             space.getexecutioncontext().subcontext_new(self)

    def descr_method__new__(space, w_subtype):
        co = space.allocate_instance(AppCoroutine, w_subtype)
        AppCoroutine.__init__(co, space)
        return space.wrap(co)

    def _get_state(space):
        return space.fromcache(AppCoState)
    _get_state = staticmethod(_get_state)

    def w_bind(self, w_func, __args__):
        space = self.space
        if self.frame is not None:
            raise OperationError(space.w_ValueError, space.wrap(
                "cannot bind a bound Coroutine"))
        state = self.costate
        thunk = _AppThunk(space, state, w_func, __args__)
        self.bind(thunk)

    def w_switch(self):
        space = self.space
        if self.frame is None:
            raise OperationError(space.w_ValueError, space.wrap(
                "cannot switch to an unbound Coroutine"))
        state = self.costate
        ec = space.getexecutioncontext()
        ec.subcontext_switch(state.current, self)
        self.switch()
        ec.subcontext_switch(state.last, state.current)
        w_ret, state.w_tempval = state.w_tempval, space.w_None
        return w_ret

    def w_kill(self):
        self.kill()

    def _userdel(self):
        if self.get_is_zombie():
            return
        self.set_is_zombie(True)
        self.space.userdel(self)

    def w_getcurrent(space):
        return space.wrap(AppCoroutine._get_state(space).current)
    w_getcurrent = staticmethod(w_getcurrent)


# _mixin_ did not work
for methname in StacklessFlags.__dict__:
    meth = getattr(StacklessFlags, methname)
    if hasattr(meth, 'im_func'):
        setattr(AppCoroutine, meth.__name__, meth.im_func)
del meth, methname

def w_get_is_zombie(space, self):
    return space.wrap(self.get_is_zombie())
AppCoroutine.w_get_is_zombie = w_get_is_zombie

def makeStaticMethod(module, classname, funcname):
    space = module.space
    space.appexec(map(space.wrap, (module, classname, funcname)), """
        (module, klassname, funcname):
            klass = getattr(module, klassname)
            func = getattr(klass, funcname)
            setattr(klass, funcname, staticmethod(func.im_func))
    """)

def post_install(module):
    makeStaticMethod(module, 'coroutine', 'getcurrent')
    space = module.space
    AppCoroutine._get_state(space).post_install()

# space.appexec("""() :

# maybe use __spacebind__ for postprocessing

AppCoroutine.typedef = TypeDef("coroutine",
    __new__ = interp2app(AppCoroutine.descr_method__new__.im_func),
    bind = interp2app(AppCoroutine.w_bind,
                      unwrap_spec=['self', W_Root, Arguments]),
    switch = interp2app(AppCoroutine.w_switch),
    kill = interp2app(AppCoroutine.w_kill),
    is_zombie = GetSetProperty(AppCoroutine.w_get_is_zombie, doc=AppCoroutine.get_is_zombie.__doc__),
    getcurrent = interp2app(AppCoroutine.w_getcurrent),
)

class AppCoState(BaseCoState):
    def __init__(self, space):
        BaseCoState.__init__(self)
        self.w_tempval = space.w_None
        self.space = space
        
    def post_install(self):
        self.current = self.main = self.last = AppCoroutine(self.space, is_main=True)
