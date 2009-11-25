import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rweakref import BaseTestRweakref

class TestJvmException(JvmTest, BaseTestRweakref):
    pass