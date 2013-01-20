import py
from rpython.translator.jvm.test.runtest import JvmTest
from rpython.translator.jvm.genjvm import detect_missing_support_programs
from rpython.translator.oosupport.test_template.backendopt import BaseTestOptimizedSwitch

class TestOptimizedSwitch(BaseTestOptimizedSwitch):
    def getcompiled(self, fn, annotation):
        detect_missing_support_programs()
        t = JvmTest()
        return t.compile(fn, None, annotation, backendopt=True)

    def test_longlong_switch(self):
        py.test.skip('fixme!')

    def test_ulonglong_switch(self):
        py.test.skip('fixme!')
