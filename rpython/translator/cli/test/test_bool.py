import py
from rpython.translator.cli.test.runtest import CliTest
from rpython.rtyper.test.test_rbool import BaseTestRbool

class TestCliBool(CliTest, BaseTestRbool):
    pass

