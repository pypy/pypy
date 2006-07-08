import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rpbc import BaseTestRPBC

class TestCliPBC(CliTest, BaseTestRPBC):
    pass
