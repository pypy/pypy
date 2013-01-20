import py
from rpython.translator.jvm.test.runtest import JvmTest
from rpython.rtyper.test.test_rweakref import BaseTestRweakref

class TestJvmException(JvmTest, BaseTestRweakref):
    pass