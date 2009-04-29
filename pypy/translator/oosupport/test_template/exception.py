import py
from pypy.rpython.test.test_exception \
     import BaseTestException as RBaseTestException

class BaseTestException(RBaseTestException):
    def test_nested_try(self):
        def helper(x):
            if x == 0:
                raise ValueError
        def dummy():
            pass        
        def fn(x):
            try:
                try:
                    helper(x)
                finally:
                    dummy()
            except ValueError, e:
                 raise
        
        self.interpret_raises(ValueError, fn, [0])

    def test_exception_not_last(self):
        def helper(x):
            if x == 0:
                raise ValueError
        def fn(x):
            helper(x)
            try:
                helper(1)
            finally:
                return -1
            return x
        self.interpret_raises(ValueError, fn, [0])

    def test_missing_return_block(self):
        class Base:
            def foo(self):
                raise ValueError

        class Derived(Base):
            def foo(self):
                return 42

        def fn(x):
            if x:
                obj = Base()
            else:
                obj = Derived()
            return obj.foo()
        assert self.interpret(fn, [0]) == 42

    def test_reraise_exception(self):
        class A(Exception):
            pass

        def raise_something(n):
            if n > 10:
                raise A
            else:
                raise Exception

        def foo(n):
            try:
                raise_something(n)
            except A:
                raise     # go through
            except Exception, e:
                return 100
            return -1

        def fn(n):
            try:
                return foo(n)
            except A:
                return 42

        res = self.interpret(fn, [100])
        assert res == 42
        res = self.interpret(fn, [0])
        assert res == 100
