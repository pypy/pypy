import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rbool import BaseTestRbool

class TestCliBool(CliTest, BaseTestRbool):
    pass

