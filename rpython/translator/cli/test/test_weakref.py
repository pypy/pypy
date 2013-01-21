import py
from rpython.translator.cli.test.runtest import CliTest
from rpython.rtyper.test.test_rweakref import BaseTestRweakref

class TestCliWeakRef(CliTest, BaseTestRweakref):
    pass
