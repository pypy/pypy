import py
from pypy.translator.c.test.test_backendoptimized import \
     TestTypedOptimizedSwitchTestCase as c_TestTypedOptimizedSwitchTestCase

class BaseTestOptimizedSwitch(c_TestTypedOptimizedSwitchTestCase):

    def CodeGenerator(self):
        return self

    def getcompiled(self, fn, annotation):
        return compile_function(fn, annotation, backendopt=True)

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
