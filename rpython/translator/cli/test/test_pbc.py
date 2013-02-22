import py
from rpython.translator.cli.test.runtest import CliTest
from rpython.rtyper.test.test_rpbc import BaseTestRPBC

class TestCliPBC(CliTest, BaseTestRPBC):
    pass
