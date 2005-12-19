"""
minimalistic coroutine implementation
"""

import os
from pypy.rpython.rstack import yield_current_frame_to_caller

def wrap_stackless_function(fn):
    from pypy.translator.translator import TranslationContext
    from pypy.translator.c.genc import CStandaloneBuilder
    from pypy.annotation.model import SomeList, SomeString
    from pypy.annotation.listdef import ListDef
    from pypy.translator.backendopt.all import backend_optimizations

    def entry_point(argv):
        os.write(1, str(fn()))
        return 0

    s_list_of_strings = SomeList(ListDef(None, SomeString()))
    s_list_of_strings.listdef.resize()
    t = TranslationContext()
    t.buildannotator().build_types(entry_point, [s_list_of_strings])
    #t.view()
    t.buildrtyper().specialize()
    backend_optimizations(t)
    cbuilder = CStandaloneBuilder(t, entry_point)
    cbuilder.stackless = True
    cbuilder.generate_source()
    cbuilder.compile()
    return cbuilder.cmdexec('')

# ____________________________________________________________

"""
Trying to build the simplest possible coroutine interface.

A coroutine is a tiny wrapper around a frame, or better
to say a one-shot continuation. This continuation is
resumed whenever we switch to the coroutine. On depart,
the coroutine is updated with its current state, that is,
the continuation is replaced. To avoid confusion with
general continuations, we are naming them as 'frame'
in the code. By frame, we are referring to the toplevel
frame as a placeholder for the whole structure appended
to it. This might be a chain of frames, or even a special
stack structure, when we implement 'hard switching'. The
abstraction layer should make this invisible.

The 'seed' of coroutines is actually the special function
yield_current_frame_to_caller(). It is, in a sense, able
to return twice. When yield_current_frame_to_caller() is
reached, it creates a resumable frame and returns it to the
caller of the current function. This frame serves as the
entry point to the coroutine.

On every entry to the coroutine, the return value of the
point where we left off is the continuation of the caller.
We need to update the caller's frame with it.
This is not necessarily the caller which created ourself.
We are therefore keeping track of the current coroutine.

The update sequence during a switch to a coroutine is:

- save the return value (caller's continuation) in the
  calling coroutine, which is still 'current'
- change current to ourself (the callee)
- invalidate our continuation by setting it to None.
"""


class CoState(object):
    pass

costate = CoState()

class CoroutineDamage(SystemError):
    pass

class Coroutine(object):

    def __init__(self):
        self.frame = None

    def bind(self, thunk):
        if self.frame is not None:
            raise CoroutineDamage
        self.frame = self._bind(thunk)

    def _bind(self, thunk):
        costate.last.frame = yield_current_frame_to_caller()
        thunk.call()
        costate.last, costate.current = costate.current, costate.main
        frame, costate.main.frame = costate.main.frame, None
        return frame

    def switch(self):
        if self.frame is None:
            raise CoroutineDamage
        costate.last, costate.current = costate.current, self
        frame, self.frame = self.frame, None
        costate.last.frame = frame.switch()

costate.current = costate.last = costate.main = Coroutine()

def output(stuff):
    os.write(2, stuff + '\n')

def test_coroutine():
    
    def g(lst, coros):
        coro_f, coro_g, coro_h = coros
        lst.append(2)
        output('g appended 2')
        coro_h.switch()
        lst.append(5)
        output('g appended 5')

    def h(lst, coros):
        coro_f, coro_g, coro_h = coros
        lst.append(3)
        output('h appended 3')
        coro_f.switch()
        lst.append(7)
        output('h appended 7')

    class T:
        def __init__(self, func, arg1, arg2):
            self.func = func
            self.arg1 = arg1
            self.arg2 = arg2
        def call(self):
            self.func(self.arg1, self.arg2)

    def f():
        lst = [1]
        coro_f = costate.main
        coro_g = Coroutine()
        coro_h = Coroutine()
        coros = [coro_f, coro_g, coro_h]
        thunk_g = T(g, lst, coros)
        output('binding g after f set 1')
        coro_g.bind(thunk_g)
        thunk_h = T(h, lst, coros)
        output('binding h after f set 1')
        coro_h.bind(thunk_h)
        output('switching to g')
        coro_g.switch()
        lst.append(4)
        output('f appended 4')
        coro_g.switch()
        lst.append(6)
        output('f appended 6')
        coro_h.switch()
        lst.append(8)
        output('f appended 8')
        n = 0
        for i in lst:
            n = n*10 + i
        return n

    data = wrap_stackless_function(f)
    assert int(data.strip()) == 12345678

def test_coroutine2():

    class TBase:
        def call(self):
            pass
        
    class T(TBase):
        def __init__(self, func, arg1, arg2):
            self.func = func
            self.arg1 = arg1
            self.arg2 = arg2
        def call(self):
            self.res = self.func(self.arg1, self.arg2)

    class T1(TBase):
        def __init__(self, func, arg1):
            self.func = func
            self.arg1 = arg1
        def call(self):
            self.res = self.func(self.arg1)

    def g(lst, coros):
        coro_f1, coro_g, coro_h = coros
        lst.append(2)
        output('g appended 2')
        coro_h.switch()
        lst.append(5)
        output('g appended 5')
        output('exiting g')
        
    def h(lst, coros):
        coro_f1, coro_g, coro_h = coros
        lst.append(3)
        output('h appended 3')
        coro_f1.switch()
        lst.append(7)
        output('h appended 7')
        output('exiting h')

    def f1(coro_f1):
        lst = [1]
        coro_g = Coroutine()
        coro_h = Coroutine()
        coros = [coro_f1, coro_g, coro_h]
        thunk_g = T(g, lst, coros)
        output('binding g after f1 set 1')
        coro_g.bind(thunk_g)
        thunk_h = T(h, lst, coros)
        output('binding h after f1 set 1')
        coro_h.bind(thunk_h)
        output('switching to g')
        coro_g.switch()
        lst.append(4)
        output('f1 appended 4')
        coro_g.switch()
        lst.append(6)
        output('f1 appended 6')
        coro_h.switch()
        lst.append(8)
        output('f1 appended 8')
        n = 0
        for i in lst:
            n = n*10 + i
        output('exiting f1')
        return n     

    def f():
        coro_f = costate.main
        coro_f1 = Coroutine()
        thunk_f1 = T1(f1, coro_f1)
        output('binding f1 after f set 1')
        coro_f1.bind(thunk_f1)
        coro_f1.switch()        
        output('return to main :-(')
        return thunk_f1.res
        
    data = wrap_stackless_function(f)
    assert int(data.strip()) == 12345678
