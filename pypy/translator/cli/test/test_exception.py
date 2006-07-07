import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_exception import BaseTestException

class TestCliException(CliTest, BaseTestException):
    pass
