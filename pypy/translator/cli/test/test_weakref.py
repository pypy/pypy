import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rweakref import BaseTestRweakref

class TestCliWeakRef(CliTest, BaseTestRweakref):
    pass
