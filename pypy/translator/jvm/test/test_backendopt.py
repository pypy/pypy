import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.backendopt import BaseTestOptimizedSwitch

class TestOptimizedSwitch(BaseTestOptimizedSwitch):
    def getcompiled(self, fn, annotation):
        t = JvmTest()
        return t._compile(fn, None, annotation, backendopt=True)
