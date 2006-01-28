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

import sys

class CoState(object):
    def __init__(self):
        self.last = self.current = Coroutine()
        self.things_to_do = False
        self.temp_exc = None
        self.del_first = None
        self.del_last = None

costate = None

class CoroutineDamage(SystemError):
    pass

class CoroutineExit(SystemExit):
    # XXX SystemExit's __init__ creates problems in bookkeeper.
    # XXX discuss this with the gurus :-)
    def __init__(self):
        pass

class Coroutine(Wrappable):

    def __init__(self):
        self.frame = None
        if costate is None:
            self.parent = self
        else:
            self.parent = costate.current
        self.thunk = None

    def bind(self, thunk):
        if self.frame is not None:
            raise CoroutineDamage
        self.thunk = thunk
        self.frame = self._bind()

    def _bind(self):
        self.parent = costate.current
        costate.last.frame = yield_current_frame_to_caller()
        try:
            self.thunk.call()
        except CoroutineExit:
            # ignore a shutdown exception
            pass
        except Exception, e:
            # redirect all unhandled exceptions to the parent
            costate.things_to_do = True
            costate.temp_exc = e
        self.thunk = None
        while self.parent.frame is None:
            # greenlet behavior is fine
            self.parent = self.parent.parent
        return self._update_state(self.parent)

    def switch(self):
        if self.frame is None:
            # considered a programming error.
            # greenlets and tasklets have different ideas about this.
            raise CoroutineDamage
        costate.last.frame = self._update_state(self).switch()
        # note that last gets updated before assignment!
        if costate.things_to_do:
            do_things_to_do(self)

    def _update_state(new):
        costate.last, costate.current = costate.current, new
        frame, new.frame = new.frame, None
        return frame
    _update_state = staticmethod(_update_state)

    def kill(self):
#        if costate.current is self:
 #           raise CoroutineExit
        if self.frame is None:
            raise CoroutineExit
        costate.things_to_do = True
        costate.temp_exc = CoroutineExit()
        self.parent = costate.current
        self.switch()

    def _kill_finally(self):
        self._userdel()
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
            postpone_deletion(self)

    def _userdel(self):
        # override this for exposed coros
        pass

    def is_alive(self):
        return self.frame is not None or self is costate.current

    def is_zombie(self):
        return self.frame is not None and check_for_zombie(self)

    def get_current():
        return costate.current
    get_current = staticmethod(get_current)


def check_for_zombie(self):
    if costate.del_first is not None:
        co = costate.del_first
        while True:
            if co is self:
                return True
            co = co.parent
            if co is costate.del_first:
                break
    return False

def postpone_deletion(obj):
    costate.things_to_do = True
    if costate.del_first is None:
        costate.del_first = costate.del_last = obj
    costate.del_last.parent = obj
    costate.del_last = obj
    obj.parent = costate.del_first

def do_things_to_do(obj):
    if costate.temp_exc is not None:
        # somebody left an unhandled exception and switched to us.
        # this both provides default exception handling and the
        # way to inject an exception, like CoroutineExit.
        e, costate.temp_exc = costate.temp_exc, None
        costate.things_to_do = costate.del_first is not None
        raise e
    if costate.del_first is not None:
        obj = costate.del_first
        costate.del_first = obj.parent
        obj.parent = costate.current
        if obj is costate.del_last:
            costate.del_first = costate.del_last = None
        obj._kill_finally()
    else:
        costate.things_to_do = False

costate = CoState()


class _AppThunk(object):

    def __init__(self, space, w_obj, args):
        self.space = space
        if space.lookup(w_obj, '__call__') is None:
            raise OperationError(
                space.w_TypeError, 
                space.mod(space.wrap('object %r is not callable'),
                          space.newtuple([w_obj])))
        self.w_func = w_obj
        self.args = args

    def call(self):
        appcostate.tempval = self.space.call_args(self.w_func, self.args)


class AppCoroutine(Coroutine): # XXX, StacklessFlags):

    def __init__(self):
        Coroutine.__init__(self)
        self.flags = 0

    def descr_method__new__(space, w_subtype):
        co = space.allocate_instance(AppCoroutine, w_subtype)
        AppCoroutine.__init__(co)
        co.space = space
        return space.wrap(co)

    def w_bind(self, w_func, __args__):
        space = self.space
        if self.frame is not None:
            raise OperationError(space.w_ValueError, space.wrap(
                "cannot bind a bound Coroutine"))
        thunk = _AppThunk(space, w_func, __args__)
        costate.current = appcostate.current
        self.bind(thunk)

    def w_switch(self):
        space = self.space
        if self.frame is None:
            raise OperationError(space.w_ValueError, space.wrap(
                "cannot switch to an unbound Coroutine"))
        costate.current = appcostate.current
        self.switch()
        appcostate.current = self
        ret, appcostate.tempval = appcostate.tempval, space.w_None
        return ret

    def w_kill(self):
        if appcostate.current is self:
            costate.current = self
        self.kill()

    def __del__(self):
        if postpone_deletion is not None:
            # we might be very late (happens with interpreted pypy)
            postpone_deletion(self)

    def _userdel(self):
        if self.get_is_zombie():
            return
        self.set_is_zombie(True)
        self.space.userdel(self)

    def get_current(space):
        return space.wrap(appcostate.current)
    get_current = staticmethod(get_current)


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
    appcostate.post_install(module.space)
    makeStaticMethod(module, 'Coroutine', 'get_current')

# space.appexec("""() :

# maybe use __spacebind__ for postprocessing

AppCoroutine.typedef = TypeDef("Coroutine",
    __new__ = interp2app(AppCoroutine.descr_method__new__.im_func),
    bind = interp2app(AppCoroutine.w_bind,
                      unwrap_spec=['self', W_Root, Arguments]),
    switch = interp2app(AppCoroutine.w_switch),
    kill = interp2app(AppCoroutine.w_kill),
    is_zombie = GetSetProperty(AppCoroutine.w_get_is_zombie, doc=AppCoroutine.get_is_zombie.__doc__),
    get_current = interp2app(AppCoroutine.get_current),
)

class AppCoState(object):
    def __init__(self):
        self.current = AppCoroutine()

    def post_install(self, space):
        appcostate.current.space = space
        appcostate.tempval = space.w_None


appcostate = AppCoState()

"""
Considerations about "current"
------------------------------
Both greenlets and tasklets have some perception
of a "current" object, which represents the
currently running tasklet/greenlet.

There is an issue how to make these structures
co-exist without interference.
One possible approach is to use the coroutines
as the basic implementation and always use
one level of indirection for the higher structures.
This allows for easy coexistence.

An alternative is to arrange things in a way that
does not interfere. Then the different classes
need to keep track of their own "current".
After a stackless task switch, stackless gets
a new current. After a greenlet's switch, greenlet
gets a new current.

"""