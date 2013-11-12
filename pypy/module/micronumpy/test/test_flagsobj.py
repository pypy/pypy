from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestFlagsObj(BaseNumpyAppTest):
    def test_repr(self):
        import numpy as np
        a = np.array([1,2,3])
        assert repr(type(a.flags)) == "<type 'numpy.flagsobj'>"

    def test_flags(self):
        import numpy as np
        a = np.array([1,2,3])
        assert a.flags.c_contiguous == True
        assert a.flags['W'] == True
        raises(KeyError, "a.flags['blah']")
        raises(KeyError, "a.flags['C_CONTIGUOUS'] = False")
        raises((TypeError, AttributeError), "a.flags.c_contiguous = False")
