import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rclass import BaseTestRclass

class TestCliClass(CliTest, BaseTestRclass):
    pass
