import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rtuple import BaseTestRtuple

class TestCliTuple(CliTest, BaseTestRtuple):
    pass
