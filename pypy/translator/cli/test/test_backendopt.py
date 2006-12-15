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

    def test_switch_naive(self):
        def fn(x):
            if x == -1:
                return 3
            elif x == 3:
                return 9
            elif x == 9:
                return -1
            return 42
        codegenerator = self.CodeGenerator()
        fn = codegenerator.getcompiled(fn, [int])
        for x in (-5,-1,0,3,9,27,48):
            assert fn(x) == fn(x)
