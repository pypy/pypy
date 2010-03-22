import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.jvm.genjvm import detect_missing_support_programs
from pypy.translator.oosupport.test_template.backendopt import BaseTestOptimizedSwitch

class TestOptimizedSwitch(BaseTestOptimizedSwitch):
    def getcompiled(self, fn, annotation):
        detect_missing_support_programs()
        t = JvmTest()
        return t.compile(fn, None, annotation, backendopt=True)

    def test_longlong_switch(self):
        py.test.skip('fixme!')

    def test_ulonglong_switch(self):
        py.test.skip('fixme!')
