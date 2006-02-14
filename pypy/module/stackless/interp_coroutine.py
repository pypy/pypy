from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.rpython.rarithmetic import intmask
from pypy.interpreter.function import StaticMethod

from pypy.rpython.rstack import yield_current_frame_to_caller
from pypy.module.stackless.stackless_flags import StacklessFlags

import sys, os

class BaseCoState(object):
    def __init__(self):
        self.current = self.main = self.last = None

    def update(self, new):
        self.last, self.current = self.current, new
        frame, new.frame = new.frame, None
        return frame

class CoState(BaseCoState):
    def __init__(self):
        BaseCoState.__init__(self)
        self.last = self.current = self.main = Coroutine(self)
        self.things_to_do = False
        self.temp_exc = None
        self.to_delete = []

    def check_for_zombie(obj):
        return co in self.to_delete
    check_for_zombie = staticmethod(check_for_zombie)

    def postpone_deletion(obj):
        costate.to_delete.append(obj)
        costate.things_to_do = True
    postpone_deletion = staticmethod(postpone_deletion)

    def do_things_to_do():
        # inlineable stub
        if costate.things_to_do:
            costate._do_things_to_do()
    do_things_to_do = staticmethod(do_things_to_do)

    def _do_things_to_do():
        if costate.temp_exc is not None:
            # somebody left an unhandled exception and switched to us.
            # this both provides default exception handling and the
            # way to inject an exception, like CoroutineExit.
            e, costate.temp_exc = costate.temp_exc, None
            costate.things_to_do = len(costate.to_delete)
            raise e
        while costate.to_delete:
            delete, costate.to_delete = costate.to_delete, []
            for obj in delete:
                obj.parent = obj.costate.current
                obj._kill_finally()
        else:
            costate.things_to_do = False
    _do_things_to_do = staticmethod(_do_things_to_do)


class CoroutineDamage(SystemError):
    pass

class CoroutineExit(SystemExit):
    # XXX SystemExit's __init__ creates problems in bookkeeper.
    def __init__(self):
        pass

DEBUG = True

def D(msg, x):
    if DEBUG:
        txt = "%s %s\n" % (msg, hex(id(x)))
        os.write(2, txt)

class Coroutine(Wrappable):

    def __init__(self, state=None):
        self.frame = None
        if state is None:
            state = costate
        self.costate = state
        self.parent = state.current

    def bind(self, thunk):
        if self.frame is not None:
            raise CoroutineDamage
        self.frame = self._bind(thunk)

    def _bind(self, thunk):
        state = self.costate
        self.parent = state.current
        state.last.frame = yield_current_frame_to_caller()
        try:
            costate.do_things_to_do()
            thunk.call()
        except CoroutineExit:
            # ignore a shutdown exception
            pass
        except Exception, e:
            # redirect all unhandled exceptions to the parent
            state.things_to_do = True
            state.temp_exc = e
        while self.parent is not None and self.parent.frame is None:
            # greenlet behavior is fine
            self.parent = self.parent.parent
        return state.update(self.parent)

    def switch(self):
        if self.frame is None:
            # considered a programming error.
            # greenlets and tasklets have different ideas about this.
            raise CoroutineDamage
        state = self.costate
        state.last.frame = state.update(self).switch()
        # note that last gets updated before assignment!
        costate.do_things_to_do()

    def kill(self):
        if self.frame is None:
            return
        costate.things_to_do = True
        costate.temp_exc = CoroutineExit()
        state = self.costate
        self.parent = state.current
        self.switch()

    def _kill_finally(self):
        try:
            self._userdel()
        except Exception:
            pass # maybe print a warning?
        self.kill()

    def __del__(self):
        # provide the necessary clean-up if this coro is left
        # with a frame.
        # note that AppCoroutine has to take care about this
        # as well, including a check for user-supplied __del__.
        # Additionally note that in the context of __del__, we are
        # not in the position to issue a switch.
        # we defer it completely.
        if self.frame is not None:
            costate.postpone_deletion(self)

    def _userdel(self):
        # override this for exposed coros
        pass

    def is_alive(self):
        return self.frame is not None or self is self.costate.current

    def is_zombie(self):
        return self.frame is not None and costate.check_for_zombie(self)

    def getcurrent():
        return costate.current
    getcurrent = staticmethod(getcurrent)


costate = None
costate = CoState()


class _AppThunk(object):

    def __init__(self, space, costate, w_obj, args):
        self.space = space
        self.costate = costate
        if space.lookup(w_obj, '__call__') is None:
            raise OperationError(
                space.w_TypeError, 
                space.mod(space.wrap('object %r is not callable'),
                          space.newtuple([w_obj])))
        self.w_func = w_obj
        self.args = args

    def call(self):
        self.costate.tempval = self.space.call_args(self.w_func, self.args)


class AppCoroutine(Coroutine): # XXX, StacklessFlags):

    def __init__(self, space):
        self.space = space
        state = self._get_state(space)
        Coroutine.__init__(self, state)
        self.flags = 0

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
        self.switch()
        ret, state.tempval = state.tempval, space.w_None
        return ret

    def w_kill(self):
        self.kill()

    def __del__(self):
        if costate.postpone_deletion is not None:
            # we might be very late (happens with interpreted pypy)
            costate.postpone_deletion(self)

    def _userdel(self):
        if self.get_is_zombie():
            return
        self.set_is_zombie(True)
        self.space.userdel(self)

    def getcurrent(space):
        return space.wrap(AppCoroutine._get_state(space).current)
    getcurrent = staticmethod(getcurrent)


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
    makeStaticMethod(module, 'Coroutine', 'getcurrent')
    space = module.space
    AppCoroutine._get_state(space).post_install()

# space.appexec("""() :

# maybe use __spacebind__ for postprocessing

AppCoroutine.typedef = TypeDef("Coroutine",
    __new__ = interp2app(AppCoroutine.descr_method__new__.im_func),
    bind = interp2app(AppCoroutine.w_bind,
                      unwrap_spec=['self', W_Root, Arguments]),
    switch = interp2app(AppCoroutine.w_switch),
    kill = interp2app(AppCoroutine.w_kill),
    is_zombie = GetSetProperty(AppCoroutine.w_get_is_zombie, doc=AppCoroutine.get_is_zombie.__doc__),
    getcurrent = interp2app(AppCoroutine.getcurrent),
)

class AppCoState(BaseCoState):
    def __init__(self, space):
        BaseCoState.__init__(self)
        self.tempval = space.w_None
        self.space = space
        
    def post_install(self):
        self.current = self.main = self.last = AppCoroutine(self.space)


"""
Basic Concept:
--------------

All concurrency is expressed by some means of coroutines.
This is the lowest possible exposable interface.

A coroutine is a structure that controls a sequence
of continuations in time. It contains a frame object
that is a restartable stack chain.
There is always a notation of a "current" and a "last"
coroutine. Current has no frame and represents the
running program. last is needed to keep track of the
coroutine that receives a new frame chain after a switch.

A costate object holds last and current.
There are different coroutine concepts existing in
parallel, like plain interp-level coroutines and
app-level structures like coroutines, greenlets and
tasklets.
Every concept is associated with its own costate object.
This allows for peaceful co-existence of many concepts.
The type of a switch is determined by the target's costate.
"""
