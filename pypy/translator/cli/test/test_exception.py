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
