from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.argument import Arguments
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.typedef import interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.rpython.rarithmetic import intmask

from pypy.rpython.rstack import yield_current_frame_to_caller

import sys

class CoState(object):
    def __init__(self):
        self.last = self.current = self.main = Coroutine()

costate = None

class CoroutineDamage(SystemError):
    pass

class Coroutine(Wrappable):

    def __init__(self):
        self.frame = None
        if costate is None:
            self.parent = self
        else:
            self.parent = costate.main

    def bind(self, thunk):
        if self.frame is not None:
            raise CoroutineDamage
        self.frame = self._bind(thunk)

    def _bind(self, thunk):
        self.parent = costate.current
        costate.last.frame = yield_current_frame_to_caller()
        thunk.call()
        if self.parent.frame is None:
            self.parent = costate.main
        return self._update_state(self.parent)

    def switch(self):
        if self.frame is None:
            raise CoroutineDamage
        costate.last.frame = self._update_state(self).switch()
        # note that last gets updated before assignment!

    def _update_state(new):
        costate.last, costate.current = costate.current, new
        frame, new.frame = new.frame, None
        return frame
    _update_state = staticmethod(_update_state)

costate = CoState()


class _AppThunk(object):

    def __init__(self, space, w_callable, args):
        self.space = space
        self.w_func = w_callable
        self.args = args

    def call(self):
        self.space.call_args(self.w_func, self.args)

class AppCoroutine(Coroutine):

    def descr_method__new__(space, w_subtype):
        co = space.allocate_instance(AppCoroutine, w_subtype)
        AppCoroutine.__init__(co)
        co.space = space
        return space.wrap(co)

    def w_bind(self, w_func, __args__):
        thunk = _AppThunk(self.space, w_func, __args__)
        self.bind(thunk)

    def w_switch(self):
        self.switch()

AppCoroutine.typedef = TypeDef("Coroutine",
    __new__ = interp2app(AppCoroutine.descr_method__new__.im_func),
    bind = interp2app(AppCoroutine.w_bind,
                      unwrap_spec=['self', W_Root, Arguments]),
    switch = interp2app(AppCoroutine.w_switch),
)
