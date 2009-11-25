
""" A small test suite for discovering whether lazy registration
of register_external functions work as intendet
"""

import py
from pypy.rpython.extfunc import lazy_register, BaseLazyRegistering, \
     registering, registering_if, extdef
from pypy.rpython.test.test_llinterp import interpret

def test_lazy_register():
    def f():
        return 3

    def g():
        return f()
    
    def reg_func():
        1/0

    lazy_register(f, reg_func)

    py.test.raises(ZeroDivisionError, interpret, g, [])

def test_lazy_register_class_raising():
    def f():
        return 3

    def g():
        return 3
    
    class LazyRegister(BaseLazyRegistering):
        def __init__(self):
            self.stuff = 8
            self.x = []

        @registering(f)
        def register_f(self):
            self.x.append(1)
            1/0

        @registering(g)
        def register_g(self):
            self.x.append(2)
            self.register(g, [], int, llimpl=lambda : self.stuff)

    py.test.raises(TypeError, "LazyRegister()")
    assert LazyRegister.instance.x == [1, 2]
    py.test.raises(ZeroDivisionError, interpret, lambda : f(), [])
    assert interpret(lambda : g(), []) == 8

def test_lazy_register_extdef():
    def g():
        return 3

    x = []

    def register_g():
        x.append('g')
        return extdef([], int, llimpl=lambda : 21)

    nothing = lazy_register(g, register_g)

    assert x == ['g']
    assert nothing is None
    assert interpret(lambda : g(), []) == 21    
    
def test_lazy_register_raising_init():
    def f():
        return 3

    def g():
        return 3

    class LazyRegister(BaseLazyRegistering):
        def __init__(self):
            1/0

        @registering(f)
        def register_f(self):
            pass

        @registering(g)
        def register_g(self):
            pass

    py.test.raises(ZeroDivisionError, interpret, lambda : f(), [])
    py.test.raises(ZeroDivisionError, interpret, lambda : g(), [])

def test_registering_if():
    class A:
        @staticmethod
        def f():
            pass

    @registering_if(A, 'f')
    def foo():
        pass

    assert foo._registering_func is A.f
    
    @registering_if(A, 'g')
    def bar():
        pass

    assert bar is None
 
