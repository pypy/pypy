"""
testing coroutines at interprepter level
"""

import os
from pypy.module.stackless.interp_coroutine import costate, Coroutine

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

def test_kill_raise_del_coro():
    class T:
        def __init__(self, func, arg):
            self.func = func
            self.arg = arg
        def call(self):
            self.func(self.arg, self)

    def g(nrec, t, count=0):
        t.count = count
        if nrec < 0:
            raise ValueError
        if nrec:
            g(nrec-1, t, count+1)
        costate.main.switch()

    def f():
        coro_g = Coroutine()
        thunk_g = T(g, 42)
        coro_g.bind(thunk_g)
        coro_g.switch()
        res = thunk_g.count
        res *= 10
        res |= coro_g.frame is not None
        # testing kill
        coro_g.kill()
        res *= 10
        res |= coro_g.frame is None
        coro_g = Coroutine()
        thunk_g = T(g, -42)
        coro_g.bind(thunk_g)
        try:
            coro_g.switch()
        except ValueError:
            res += 500
        return res
    
    data = wrap_stackless_function(f)
    assert int(data.strip()) == 4711
