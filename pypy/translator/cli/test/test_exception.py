import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_exception import BaseTestException

class TestCliException(CliTest, BaseTestException):
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
