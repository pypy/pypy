from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter.error import OperationError

from pypy.module._stackless.rcoroutine import Coroutine, BaseCoState
from pypy.module._stackless.rcoroutine import AbstractThunk, syncstate
from pypy.module._stackless.interp_coroutine import makeStaticMethod


class GreenletThunk(AbstractThunk):

    def __init__(self, greenlet):
        self.greenlet = greenlet

    def call(self):
        greenlet = self.greenlet
        greenlet.active = True
        try:
            space = greenlet.space
            args_w = greenlet.costate.args_w
            __args__ = Arguments(space, args_w)
            try:
                w_run = space.getattr(space.wrap(greenlet), space.wrap('run'))
                greenlet.w_callable = None
                w_result = space.call_args(w_run, __args__)
            except OperationError, operror:
                if not operror.match(space, greenlet.costate.w_GreenletExit):
                    raise
                w_result = operror.get_w_value(space)
        finally:
            greenlet.active = False
        greenlet.costate.args_w = [w_result]

class AppGreenletCoState(BaseCoState):
    def __init__(self, space):
        BaseCoState.__init__(self)
        self.args_w = None
        self.space = space
        self.w_GreenletExit  = get(space, "GreenletExit")
        self.w_GreenletError = get(space, "GreenletError")

    def post_install(self):
        self.current = self.main = AppGreenlet(self.space, is_main=True)

class AppGreenlet(Coroutine):
    def __init__(self, space, w_callable=None, is_main=False):
        Coroutine.__init__(self, self._get_state(space))
        self.space = space
        self.w_callable = w_callable
        self.active = is_main
        self.subctx = space.getexecutioncontext().Subcontext()
        if is_main:
            self.subctx.clear_framestack()      # wack
        else:
            self.bind(GreenletThunk(self))

    def descr_method__new__(space, w_subtype, __args__):
        co = space.allocate_instance(AppGreenlet, w_subtype)
        AppGreenlet.__init__(co, space)
        return space.wrap(co)

    def descr_method__init__(self, w_run=NoneNotWrapped,
                                   w_parent=NoneNotWrapped):
        if w_run is not None:
            self.set_run(w_run)
        if w_parent is not None:
            self.set_parent(w_parent)

    def _get_state(space):
        return space.fromcache(AppGreenletCoState)
    _get_state = staticmethod(_get_state)

    def hello(self):
        ec = self.space.getexecutioncontext()
        self.subctx.enter(ec)

    def goodbye(self):
        ec = self.space.getexecutioncontext()
        self.subctx.leave(ec)

    def w_getcurrent(space):
        return space.wrap(AppGreenlet._get_state(space).current)
    w_getcurrent = staticmethod(w_getcurrent)

    def w_switch(self, args_w):
        # Find the switch target - it might be a parent greenlet
        space = self.space
        costate = self.costate
        target = self
        while target.isdead():
            target = target.parent
            assert isinstance(target, AppGreenlet)
        # Switch to it
        costate.args_w = args_w
        if target is not costate.current:
            target.switch()
        else:
            # case not handled in Coroutine.switch()
            syncstate._do_things_to_do()
        result_w = costate.args_w
        costate.args_w = None
        # costate.args_w can be set to None above for throw(), but then
        # switch() should have raised.  At this point cosstate.args_w != None.
        assert result_w is not None
        # Return the result of a switch, packaging it in a tuple if
        # there is more than one value.
        if len(result_w) == 1:
            return result_w[0]
        return space.newtuple(result_w)

    def w_throw(self, w_type=None, w_value=None, w_traceback=None):
        space = self.space
        if space.is_w(w_type, space.w_None):
            w_type = self.costate.w_GreenletExit
        # Code copied from RAISE_VARARGS but slightly modified.  Not too nice.
        operror = OperationError(w_type, w_value)
        operror.normalize_exception(space)
        if not space.is_w(w_traceback, space.w_None):
            from pypy.interpreter import pytraceback
            tb = space.interpclass_w(w_traceback)
            if tb is None or not space.is_true(space.isinstance(tb, 
                space.gettypeobject(pytraceback.PyTraceback.typedef))):
                raise OperationError(space.w_TypeError,
                      space.wrap("throw: arg 3 must be a traceback or None"))
            operror.application_traceback = tb
        # Dead greenlet: turn GreenletExit into a regular return
        if self.isdead() and operror.match(space, self.costate.w_GreenletExit):
            args_w = [operror.get_w_value(space)]
        else:
            syncstate.push_exception(operror)
            args_w = None
        return self.w_switch(args_w)

    def _userdel(self):
        self.space.userdel(self.space.wrap(self))

    def isdead(self):
        return self.thunk is None and not self.active

    def w_get_is_dead(self, space):
        return space.newbool(self.isdead())

    def descr__nonzero__(self):
        return self.space.newbool(self.active)

    def w_get_run(self, space):
        w_run = self.w_callable
        if w_run is None:
            raise OperationError(space.w_AttributeError, space.wrap("run"))
        return w_run

    def set_run(self, w_run):
        space = self.space
        if self.thunk is None:
            raise OperationError(space.w_AttributeError,
                                 space.wrap("run cannot be set "
                                            "after the start of the greenlet"))
        self.w_callable = w_run

    def w_set_run(self, space, w_run):
        self.set_run(w_run)

    def w_del_run(self, space):
        if self.w_callable is None:
            raise OperationError(space.w_AttributeError, space.wrap("run"))
        self.w_callable = None

    def w_get_parent(self, space):
        return space.wrap(self.parent)

    def set_parent(self, w_parent):
        space = self.space
        newparent = space.interp_w(AppGreenlet, w_parent)
        if newparent.costate is not self.costate:
            raise OperationError(self.costate.w_GreenletError,
                                 space.wrap("invalid foreign parent"))
        curr = newparent
        while curr:
            if curr is self:
                raise OperationError(space.w_ValueError,
                                     space.wrap("cyclic parent chain"))
            curr = curr.parent
        self.parent = newparent

    def w_set_parent(self, space, w_parent):
        self.set_parent(w_parent)

    def w_get_frame(self, space):
        if not self.active or self.costate.current is self:
            f = None
        else:
            f = self.subctx.topframe
        return space.wrap(f)

def get(space, name):
    w_module = space.getbuiltinmodule('_stackless')
    return space.getattr(w_module, space.wrap(name))

def post_install(module):
    "NOT_RPYTHON"
    makeStaticMethod(module, 'greenlet', 'getcurrent')
    space = module.space
    state = AppGreenlet._get_state(space)
    state.post_install()
    w_greenlet = get(space, 'greenlet')
    # HACK HACK HACK
    # make the typeobject mutable for a while
    from pypy.objspace.std.typeobject import W_TypeObject
    assert isinstance(w_greenlet, W_TypeObject)
    old_flag = w_greenlet.flag_heaptype
    w_greenlet.flag_heaptype = True
    space.appexec([w_greenlet,
                   state.w_GreenletExit,
                   state.w_GreenletError], """
    (greenlet, exit, error):
        greenlet.GreenletExit = exit
        greenlet.error = error
    """)
    w_greenlet.flag_heaptype = old_flag

AppGreenlet.typedef = TypeDef("greenlet",
    __new__ = interp2app(AppGreenlet.descr_method__new__.im_func),
    __init__ = interp2app(AppGreenlet.descr_method__init__),
    switch = interp2app(AppGreenlet.w_switch),
    dead = GetSetProperty(AppGreenlet.w_get_is_dead),
    run = GetSetProperty(AppGreenlet.w_get_run,
                         AppGreenlet.w_set_run,
                         AppGreenlet.w_del_run),
    parent = GetSetProperty(AppGreenlet.w_get_parent,
                            AppGreenlet.w_set_parent),
    getcurrent = interp2app(AppGreenlet.w_getcurrent),
    throw = interp2app(AppGreenlet.w_throw),
    gr_frame = GetSetProperty(AppGreenlet.w_get_frame),
    __nonzero__ = interp2app(AppGreenlet.descr__nonzero__),
    __module__ = '_stackless',
)
