from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import StaticMethod

from pypy.module._stackless.stackless_flags import StacklessFlags
from pypy.module._stackless.interp_coroutine import Coroutine, BaseCoState, AbstractThunk
from pypy.module._stackless.coroutine import _AppThunk, makeStaticMethod

class GreenletThunk(AbstractThunk):

    def __init__(self, space, costate, greenlet):
        self.space = space
        self.costate = costate
        self.greenlet = greenlet

    def call(self):
        __args__ = self.costate.__args__
        assert __args__ is not None
        try:
            w_result = self.space.call_args(self.greenlet.w_callable, __args__)
        except OperationError, operr:
            self.greenlet.w_dead = self.space.w_True
            self.costate.operr = operr
            w_result = self.space.w_None
        else:
            self.greenlet.w_dead = self.space.w_True
        while 1:
            __args__ = Arguments(self.space, [w_result])
            try:
                w_result = self.greenlet.w_parent.w_switch(__args__)
            except OperationError, operr:
                self.costate.operr = operr

class AppGreenletCoState(BaseCoState):
    def __init__(self, space):
        BaseCoState.__init__(self)
        self.__args__ = None
        self.space = space
        self.operr = None
        
    def post_install(self):
        self.current = self.main = AppGreenlet(self.space, is_main=True)

class GreenletExit(Exception):
    pass

class AppGreenlet(Coroutine):
    def __init__(self, space, w_callable=None, is_main=False):
        self.space = space
        self.w_callable = w_callable
        self.w_dead = space.w_False
        self.has_ever_run = False or is_main
        self.is_main = is_main
        state = self._get_state(space)
        if is_main:
            self.w_parent = None
        else:
            w_parent = state.current
            assert isinstance(w_parent, AppGreenlet)
            self.w_parent = w_parent
        Coroutine.__init__(self, state)
        if not is_main:
            space.getexecutioncontext().subcontext_new(self)
            self.bind(GreenletThunk(space, state, self))

    def descr_method__new__(space, w_subtype, w_callable):
        co = space.allocate_instance(AppGreenlet, w_subtype)
        AppGreenlet.__init__(co, space, w_callable)
        return space.wrap(co)

    def _get_state(space):
        return space.fromcache(AppGreenletCoState)
    _get_state = staticmethod(_get_state)

    def hello(self):
        ec = self.space.getexecutioncontext()
        ec.subcontext_enter(self)

    def goodbye(self):
        ec = self.space.getexecutioncontext()
        ec.subcontext_leave(self)

    def w_getcurrent(space):
        return space.wrap(AppGreenlet._get_state(space).current)
    w_getcurrent = staticmethod(w_getcurrent)

    def w_switch(self, __args__):
        #print "switch", __args__, id(self)
        if __args__.num_kwds():
            raise OperationError(
                self.space.w_TypeError,
                self.space.wrap("switch() takes not keyword arguments"))
        self.has_ever_run = True
        self.costate.__args__ = __args__
        self.switch()
        #print "after switch"
        #print self.costate.__args__
        if self.costate.operr is not None:
            operr = self.costate.operr
            self.costate.operr = None
            raise operr
        args_w, kwds_w = self.costate.__args__.unpack()
        if args_w is None:
            return self.space.w_None
        if len(args_w) == 1:
            return args_w[0]
        return self.space.newtuple(args_w)

    def w_throw(self, w_exception):
        self.costate.operr = OperationError(w_exception, self.space.wrap(""))
        self.w_switch(Arguments(self.space, []))

    def _userdel(self):
        self.space.userdel(self)

def w_get_is_dead(space, w_self):
    self = space.interp_w(AppGreenlet, w_self)
    return self.w_dead

def descr__bool__(space, w_self):
    self = space.interp_w(AppGreenlet, w_self)
    return space.wrap(self.has_ever_run and not space.is_true(self.w_dead))

def w_get_parent(space, w_self):
    self = space.interp_w(AppGreenlet, w_self)
    if self.w_parent is not None:
        return self.w_parent
    else:
        return space.w_None

def w_set_parent(space, w_self, w_parent):
    self = space.interp_w(AppGreenlet, w_self)
    newparent = space.interp_w(AppGreenlet, w_parent)
    curr = newparent
    while 1:
        if space.is_true(space.is_(self, curr)):
            raise OperationError(space.w_ValueError, space.wrap("cyclic parent chain"))
        if not curr.w_parent is None:
            break
        curr = curr.w_parent
    self.w_parent = newparent

def w_get_frame(space, w_self):
    self = space.interp_w(AppGreenlet, w_self)    
    if not self.has_ever_run or space.is_true(self.w_dead):
        return space.w_None
    try:
        return self.framestack.top(0)
    except IndexError:
        return space.w_None

def get(space, name):
    w_module = space.getbuiltinmodule('_stackless')
    return space.getattr(w_module, space.wrap(name))

def post_install(module):
    makeStaticMethod(module, 'greenlet', 'getcurrent')
    space = module.space
    AppGreenlet._get_state(space).post_install()
    w_module = space.getbuiltinmodule('_stackless')
    space.appexec([w_module, get(space, "GreenletExit"),
                   get(space, "GreenletError")], """
    (mod, exit, error):
        mod.greenlet.GreenletExit = exit
        mod.greenlet.error = error
    """)

AppGreenlet.typedef = TypeDef("greenlet",
    __new__ = interp2app(AppGreenlet.descr_method__new__.im_func),
    switch = interp2app(AppGreenlet.w_switch,
                        unwrap_spec=['self', Arguments]),
    dead = GetSetProperty(w_get_is_dead),
    parent = GetSetProperty(w_get_parent, w_set_parent),
    getcurrent = interp2app(AppGreenlet.w_getcurrent),
    throw = interp2app(AppGreenlet.w_throw),
    gr_frame = GetSetProperty(w_get_frame),
    __nonzero__ = interp2app(descr__bool__),
#    GreenletExit = GreenletExit,
#    error = GreenletExit,
    __module__ = '_stackless',
)

