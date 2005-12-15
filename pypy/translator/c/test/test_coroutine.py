"""
Hi Armin:
When I set DEBUG to False, the program crashes. Maybe I'm doing something
wrong and re-using some used continuation, don't know.
So I was trying to set things to Nonw after becoming invalid, but
that breaks the rtyper.
"""

DEBUG = False
# set to true and compilation crashes
USE_NONE = False
# set to true and rtyper crashes

# the above are exclusive right now

CHECKED_IN = True
# set this to false to skip skipping :-)

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

On evetry entry to the coroutine, the return value of the
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

    if DEBUG:
        def __init__(self):
            self._switchable = False

    if USE_NONE:
        def __init__(self):
            self.frame = None

    def bind(self, thunk):
        if USE_NONE:
            assert self.frame is None
        self.frame = self._bind(thunk)

    def _bind(self, thunk):
        if self is costate.current or self is costate.main:
            raise CoroutineDamage
        frame = yield_current_frame_to_caller()
        costate.current.frame = frame
        if DEBUG:
            costate.current.switchable = True
            assert self._switchable == True
            self._switchable = False
        costate.current = self
        thunk.call()
        return self.frame # just for the annotator

    def switch(self):
        if DEBUG:
            assert self._switchable == True
            assert costate.current._switchable == False
        if USE_NONE:
            assert costate.current.frame is None
            assert self.frame is not None
        frame = self.frame.switch()
        if DEBUG:
            assert costate.current._switchable == False
            costate.current._switchable = True
        if USE_NONE:
            assert costate.current.frame is None
        costate.current.frame = frame
        costate.current = self
        # XXX support: self.frame = None

costate.current = costate.main = Coroutine()

def output(stuff):
    os.write(2, stuff + '\n')

def test_coroutine():
    if CHECKED_IN:
        import py.test
        py.test.skip("in-progress")
    
    def g(lst):
        lst.append(2)
        output('g appended 2')
        costate.main.switch()
        lst.append(4)
        output('g appended 4')
        costate.main.switch()
        lst.append(6)
        output('g appended 6')

    class T:
        def __init__(self, func, arg):
            self.func = func
            self.arg = arg
        def call(self):
            self.func(self.arg)

    def f():
        lst = [1]
        coro_g = Coroutine()
        t = T(g, lst)
        output('binding after f set 1')
        coro_g.bind(t)
        output('switching')
        coro_g.switch()
        lst.append(3)
        output('f appended 3')
        coro_g.switch()
        lst.append(5)
        output('f appended 5')
        coro_g.switch()
        lst.append(7)
        output('f appended 7')
        n = 0
        for i in lst:
            n = n*10 + i
        return n

    data = wrap_stackless_function(f)
    assert int(data.strip()) == 1234567
