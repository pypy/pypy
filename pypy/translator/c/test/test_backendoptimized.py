import py
from pypy.translator.c.test.test_typed import TestTypedTestCase as _TestTypedTestCase
from pypy.translator.backendopt.all import backend_optimizations
from pypy.rpython import objectmodel
from pypy.rpython.rarithmetic import r_uint, r_longlong, r_ulonglong

class TestTypedOptimizedTestCase(_TestTypedTestCase):

    def process(self, t):
        _TestTypedTestCase.process(self, t)
        self.t = t
        backend_optimizations(t, raisingop2direct_call_all=False, merge_if_blocks_to_switch=False)

    def test_remove_same_as(self):
        def f(n=bool):
            if bool(bool(bool(n))):
                return 123
            else:
                return 456
        fn = self.getcompiled(f)
        assert f(True) == 123
        assert f(False) == 456

    def test__del__(self):
        import os
        class B(object):
            pass
        b = B()
        b.nextid = 0
        b.num_deleted = 0
        class A(object):
            def __init__(self):
                self.id = b.nextid
                b.nextid += 1

            def __del__(self):
                b.num_deleted += 1

        def f(x=int):
            a = A()
            for i in range(x):
                a = A()
            return b.num_deleted

        fn = self.getcompiled(f)
        res = f(5)
        assert res == 5
        res = fn(5)
        # translated function looses its last reference earlier
        assert res == 6
    
    def test_del_inheritance(self):
        class State:
            pass
        s = State()
        s.a_dels = 0
        s.b_dels = 0
        class A(object):
            def __del__(self):
                s.a_dels += 1
        class B(A):
            def __del__(self):
                s.b_dels += 1
        class C(A):
            pass
        def f():
            A()
            B()
            C()
            A()
            B()
            C()
            return s.a_dels * 10 + s.b_dels
        res = f()
        assert res == 42
        fn = self.getcompiled(f)
        res = fn()
        assert res == 42


class TestTypedOptimizedSwitchTestCase:

    class CodeGenerator(_TestTypedTestCase):
        def process(self, t):
            _TestTypedTestCase.process(self, t)
            self.t = t
            backend_optimizations(t, merge_if_blocks_to_switch=True)

    def test_int_switch(self):
        def f(x=int):
            if x == 3:
                return 9
            elif x == 9:
                return 27
            elif x == 27:
                return 3
            return 0
        codegenerator = self.CodeGenerator()
        fn = codegenerator.getcompiled(f)
        for x in (0,1,2,3,9,27,48, -9):
            assert fn(x) == f(x)

    def test_uint_switch(self):
        def f(x=r_uint):
            if x == r_uint(3):
                return 9
            elif x == r_uint(9):
                return 27
            elif x == r_uint(27):
                return 3
            return 0
        codegenerator = self.CodeGenerator()
        fn = codegenerator.getcompiled(f)
        for x in (0,1,2,3,9,27,48):
            assert fn(x) == f(x)

    def test_longlong_switch(self):
        def f(x=r_longlong):
            if x == r_longlong(3):
                return 9
            elif x == r_longlong(9):
                return 27
            elif x == r_longlong(27):
                return 3
            return 0
        codegenerator = self.CodeGenerator()
        fn = codegenerator.getcompiled(f)
        for x in (0,1,2,3,9,27,48, -9):
            assert fn(x) == f(x)

    def test_ulonglong_switch(self):
        def f(x=r_ulonglong):
            if x == r_ulonglong(3):
                return 9
            elif x == r_ulonglong(9):
                return 27
            elif x == r_ulonglong(27):
                return 3
            return 0
        codegenerator = self.CodeGenerator()
        fn = codegenerator.getcompiled(f)
        for x in (0,1,2,3,9,27,48, -9):
            assert fn(x) == f(x)

    def test_chr_switch(self):
        def f(y=int):
            x = chr(y)
            if x == 'a':
                return 'b'
            elif x == 'b':
                return 'c'
            elif x == 'c':
                return 'd'
            return '@'
        codegenerator = self.CodeGenerator()
        fn = codegenerator.getcompiled(f)
        for x in 'ABCabc@':
            y = ord(x)
            assert fn(y) == f(y)

    def test_unichr_switch(self):
        def f(y=int):
            x = unichr(y)
            if x == u'a':
                return 'b'
            elif x == u'b':
                return 'c'
            elif x == u'c':
                return 'd'
            return '@'
        codegenerator = self.CodeGenerator()
        fn = codegenerator.getcompiled(f)
        for x in u'ABCabc@':
            y = ord(x)
            assert fn(y) == f(y)

class TestTypedOptimizedRaisingOps:

    class CodeGenerator(_TestTypedTestCase):
        def process(self, t):
            _TestTypedTestCase.process(self, t)
            self.t = t

    def test_int_floordiv_zer(self):
        def f(x=int):
            try:
                y = 123 / x
            except:
                y = 456
            return y
        codegenerator = self.CodeGenerator()
        fn = codegenerator.getcompiled(f)
        for x in (0,1,2,3,9,27,48, -9):
            assert fn(x) == f(x)
