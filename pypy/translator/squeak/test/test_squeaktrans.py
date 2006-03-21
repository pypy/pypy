import os
import py
from pypy.translator.test import snippet
from pypy.translator.squeak.test.runtest import compile_function

class TestGenSqueak:

    def test_theanswer(self):
        def theanswer():
            return 42
        fn = compile_function(theanswer)
        assert fn() == "42"

    def test_simplemethod(self):
        class A:
            def m(self):
                return 42
        def simplemethod():
            return A().m()
        fn = compile_function(simplemethod)
        assert fn() == "42"

    def test_argfunction(self):
        def function(i, j=2):
            return i + j
        fn = compile_function(function, [int, int])
        assert fn(1, 3) == "4"

    def test_argmethod(self):
        class A:
            def m(self, i, j, h=2):
                return i + j + h
        def simplemethod(i):
            return A().m(i, j=3)
        fn = compile_function(simplemethod, [int])
        assert fn(1) == "6"

    def test_nameclash_classes(self):
        from pypy.translator.squeak.test.support import A as A2
        class A:
            def m(self, i): return 2 + i
        class Functions:
            def m(self, i): return 1 + i
        def f():
            return A().m(0) + A2().m(0) + Functions().m(-1)
        fn = compile_function(f)
        assert fn() == "3"

    def test_nameclash_classes_mean(self):
        class A:
            def m(self, i): return 1 + i
        A2 = A
        class A:
            def m(self, i): return 2 + i
        def f():
            return A().m(0) + A2().m(0)
        fn = compile_function(f)
        assert fn() == "3"

    def test_nameclash_camel_case(self):
        class ASomething:
            def m(self, i): return 1 + i
        class A_Something:
            def m(self, i): return 2 + i
        def f():
            x = ASomething().m(0) + A_Something().m(0)
            return x + ASomething().m(0) + A_Something().m(0)
        fn = compile_function(f)
        assert fn() == "6"

    def test_nameclash_functions(self):
        from pypy.translator.squeak.test.support import f as f2
        def f(i):
            return i + 2
        def g():
            return f(0) + f2(0)
        fn = compile_function(g)
        assert fn() == "3"

    def test_nameclash_methods(self):
        class A:
            def some_method(self, i): return i + 1
            def someMethod(self, i): return i + 2
        def f():
            a = A()
            return a.some_method(0) + a.someMethod(0)
        fn = compile_function(f)
        assert fn() == "3"

    def test_nameclash_fields(self):
        class A:
            def m(self, i):
                self.var1 = i
                self.var_1 = i + 1
        def f():
            a = A()
            a.m(1)
            return a.var1 + a.var_1
        fn = compile_function(f)
        assert fn() == "3"

    def test_direct_call(self):
        def h(i):
            return g(i) + 1 # another call to g to try to trap GenSqueak
        def g(i):
            return i + 1 
        def f(i):
            return h(i) + g(i)
        fn = compile_function(f, [int])
        assert fn(1) == "5"

    def test_getfield_setfield(self):
        class A:
            def set(self, i):
                self.i_var = i
            def inc(self):
                self.i_var = self.i_var + 1
        def f(i):
            a = A()
            a.set(i)
            i = a.i_var
            a.i_var = 3
            a.inc()
            return i + a.i_var
        fn = compile_function(f, [int])
        assert fn(2) == "6"

    def test_classvars(self):
        class A: i = 1
        class B(A): i = 2
        def pick(i):
            if i == 1:
               c = A
            else:
               c = B
            return c
        def f(i):
            c = pick(i)
            return c.i
        fn = compile_function(f, [int])
        assert fn(1) == "1"
        assert fn(2) == "2"

class TestException:

    def test_simpleexception(self):
        def raising(i):
            if i > 0:
                raise ValueError
            else:
                return i + 1
        def f(i):
            try:
                return raising(i)
            except ValueError, val:
                return i - 1
        fn = compile_function(f, [int])
        assert fn(-1) == "0"
        assert fn(2) == "1"

    def test_exceptbranch(self):
        def raising(i):
            if i == 0:
                raise ValueError
            elif i < 0:
                raise AttributeError
            else:
                return i + 1
        def f(i):
            try:
                return raising(i)
            except ValueError:
                return i
            except AttributeError:
                return -i
        fn = compile_function(f, [int])
        assert fn(-1) == "1"
        assert fn(0) == "0"
        assert fn(2) == "3"

    def test_exceptreraise(self):
        def raising(i):
            if i == 0:
                raise ValueError
            elif i < 0:
                raise AttributeError
            else:
                return i + 1
        def f(i):
            try:
                return raising(i)
            except ValueError:
                return i
        def g(i):
            try:
                return f(i)
            except AttributeError:
                return -i
        fn = compile_function(g, [int])
        assert fn(-2) == "2"

