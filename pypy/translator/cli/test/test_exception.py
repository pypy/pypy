import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_exception import BaseTestException

class TestCliException(CliTest, BaseTestException):
    use_exception_transformer = False

    def interpret(self, *args, **kwds):
        kwds['exctrans'] = self.use_exception_transformer
        return CliTest.interpret(self, *args, **kwds)

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

    def test_raise_and_catch_other(self):
        pass

    def test_raise_prebuilt_and_catch_other(self):
        pass

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

    def test_missing_handler(self):
        def foo(x):
            if x:
                raise ValueError
        
        def fn(x):
            try:
                foo(x)
            except ValueError:
                raise
            return 42
        assert self.interpret(fn, [0], backendopt=False) == 42
        self.interpret_raises(ValueError, fn, [1], backendopt=False)


class TestCliExceptionTransformer(TestCliException):
    use_exception_transformer = True
