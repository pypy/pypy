"""
Basic Concept:
--------------

All concurrency is expressed by some means of coroutines.
This is the lowest possible exposable interface.

A coroutine is a structure that controls a sequence
of continuations in time. It contains a frame object
that is a restartable stack chain. This frame object
is updated on every switch.

The frame can be None. Either the coroutine is not yet
bound, or it is the current coroutine of some costate.
See below. XXX rewrite a definition of these terms.

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

from pypy.interpreter.baseobjspace import Wrappable
from pypy.rpython.rstack import yield_current_frame_to_caller, resume_point
from pypy.rpython.objectmodel import we_are_translated

try:
    from py.magic import greenlet
    main_greenlet = greenlet.getcurrent()
    class MyGreenlet(object):
        def __init__(self, thunk=None, curr=False):
            if curr:
                self.greenlet = greenlet.getcurrent()
            else:
                self.greenlet = greenlet(thunk)
        def switch(self):
            last = MyGreenlet(curr=True)
# XXX unclear what to do there
#            self.greenlet.parent = greenlet.getcurrent()
            return self.greenlet.switch(last)
    GreenletExit = greenlet.GreenletExit
except ImportError:
    def greenlet(*args, **kwargs):
        raise NotImplementedError("need either greenlets or a translated version of pypy")
    class GreenletExit(Exception):
        pass

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
        main_coroutine_getter._get_default_costate().to_delete.append(obj)
        main_coroutine_getter._get_default_costate().things_to_do = True
    postpone_deletion = staticmethod(postpone_deletion)

    def do_things_to_do():
        # inlineable stub
        if main_coroutine_getter._get_default_costate().things_to_do:
            main_coroutine_getter._get_default_costate()._do_things_to_do()
    do_things_to_do = staticmethod(do_things_to_do)

    def _do_things_to_do():
        main_costate = main_coroutine_getter._get_default_costate()
        if main_costate.temp_exc is not None:
            # somebody left an unhandled exception and switched to us.
            # this both provides default exception handling and the
            # way to inject an exception, like CoroutineExit.
            e, main_costate.temp_exc = main_costate.temp_exc, None
            main_costate.things_to_do = len(main_costate.to_delete)
            raise e
        while main_costate.to_delete:
            delete, main_costate.to_delete = main_costate.to_delete, []
            for obj in delete:
                obj.parent = obj.costate.current
                obj._kill_finally()
        else:
            main_costate.things_to_do = False
    _do_things_to_do = staticmethod(_do_things_to_do)


class CoroutineDamage(SystemError):
    pass

class MainCoroutineGetter(object):
    def __init__(self):
        self.costate = None
    def _get_default_costate(self):
        if self.costate is None:
            costate = CoState()
            self.costate = costate
            return costate
        return self.costate
            
main_coroutine_getter = MainCoroutineGetter()

class CoroutineExit(SystemExit):
    # XXX SystemExit's __init__ creates problems in bookkeeper.
    def __init__(self):
        pass

def get_exit_class():  # XXX hum
    if we_are_translated():
        return CoroutineExit
    else:
        return GreenletExit

class AbstractThunk(object):
    def call(self):
        raise NotImplementedError("abstract base class")

class Coroutine(Wrappable):
    def __init__(self, state=None):
        self.frame = None
        if state is None:
            state = main_coroutine_getter._get_default_costate()
        self.costate = state
        self.parent = None

    def _get_default_parent(self):
        return main_coroutine_getter._get_default_costate().current

    def bind(self, thunk):
        assert isinstance(thunk, AbstractThunk)
        if self.frame is not None:
            raise CoroutineDamage
        if self.parent is None:
            self.parent = self._get_default_parent()
        assert self.parent is not None
        if we_are_translated():
            self.frame = self._bind(thunk)
        else:
            self.frame = self._greenlet_bind(thunk)

    def _greenlet_bind(self, thunk):
        state = self.costate
        self.parent = state.current
        assert self.parent is not None
        def _greenlet_execute(incoming_frame):
            return self._execute(thunk, state, incoming_frame)
        return MyGreenlet(_greenlet_execute)

    def _bind(self, thunk):
        state = self.costate
        self.parent = state.current
        incoming_frame = yield_current_frame_to_caller()
        return self._execute(thunk, state, incoming_frame)

    def _execute(self, thunk, state, incoming_frame):
        left = state.last
        left.frame = incoming_frame
        left.goodbye()
        self.hello()
        try:
            main_coroutine_getter._get_default_costate().do_things_to_do()
            thunk.call()
            resume_point("coroutine__bind", self, state)
        except GreenletExit:
            # ignore a shutdown exception
            pass
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
        incoming_frame = state.update(self).switch()
        resume_point("coroutine_switch", self, state, returns=incoming_frame)
        left = state.last
        left.frame = incoming_frame
        left.goodbye()
        self.hello()
        main_coroutine_getter._get_default_costate().do_things_to_do()

    def kill(self):
        if self.frame is None:
            return
        main_coroutine_getter._get_default_costate().things_to_do = True
        main_coroutine_getter._get_default_costate().temp_exc = get_exit_class()()
        state = self.costate
        self.parent = state.current
        self.switch()

    def _kill_finally(self):
        try:
            self._userdel()
        except Exception:
            pass # maybe print a warning?
        self.kill()

    def X__del__(self):
        # provide the necessary clean-up if this coro is left
        # with a frame.
        # note that AppCoroutine has to take care about this
        # as well, including a check for user-supplied __del__.
        # Additionally note that in the context of __del__, we are
        # not in the position to issue a switch.
        # we defer it completely.
        if self.frame is not None:
            main_coroutine_getter._get_default_costate().postpone_deletion(self)

    def _userdel(self):
        # override this for exposed coros
        pass

    def is_alive(self):
        return self.frame is not None or self is self.costate.current

    def is_zombie(self):
        return self.frame is not None and main_coroutine_getter._get_default_costate().check_for_zombie(self)

    def getcurrent():
        return main_coroutine_getter._get_default_costate().current
    getcurrent = staticmethod(getcurrent)

    def getmain():
        return main_coroutine_getter._get_default_costate().main
    getmain = staticmethod(getmain)

    def hello(self):
        "Called when execution is transferred into this coroutine."

    def goodbye(self):
        "Called just after execution is transferred away from this coroutine."

# _________________________________________________
