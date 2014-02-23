from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestAppBridge(BaseNumpyAppTest):
    def test_array_methods(self):
        import numpy as np
        a = np.array(1.5)
        for op in [a.mean, a.var, a.std]:
            try:
                op()
            except ImportError as e:
                assert str(e) == 'No module named numpy.core'
