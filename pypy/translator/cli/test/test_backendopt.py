import py
from pypy.translator.cli.test.runtest import compile_function
from pypy.translator.c.test.test_backendoptimized import \
     TestTypedOptimizedSwitchTestCase as c_TestTypedOptimizedSwitchTestCase

class CTestCompat:
    backend_opt = {
        'merge_if_blocks': True
        }

    def CodeGenerator(self):
        return self

    def getcompiled(self, fn, annotation):
        return compile_function(fn, annotation, backend_opt=self.backend_opt)

class TestOptimizedSwitchTestCase(CTestCompat, c_TestTypedOptimizedSwitchTestCase):
    def test_longlong_switch(self):
        py.test.skip('Not yet supported')

    def test_ulonglong_switch(self):
        py.test.skip('Not yet supported')
