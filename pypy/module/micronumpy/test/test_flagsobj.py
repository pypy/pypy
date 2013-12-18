from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestFlagsObj(BaseNumpyAppTest):
    def test_repr(self):
        import numpy as np
        a = np.array([1,2,3])
        assert repr(type(a.flags)) == "<type 'numpy.flagsobj'>"

    def test_array_flags(self):
        import numpy as np
        a = np.array([1,2,3])
        assert a.flags.c_contiguous == True
        assert a.flags['W'] == True
        assert a.flags.fnc == False
        assert a.flags.forc == True
        assert a.flags['FNC'] == False
        assert a.flags['FORC'] == True
        raises(KeyError, "a.flags['blah']")
        raises(KeyError, "a.flags['C_CONTIGUOUS'] = False")
        raises((TypeError, AttributeError), "a.flags.c_contiguous = False")

    def test_scalar_flags(self):
        import numpy as np
        a = np.int32(2)
        assert a.flags.c_contiguous == True

    def test_compare(self):
        import numpy as np
        a = np.array([1,2,3])
        b = np.array([4,5,6,7])
        assert a.flags == b.flags
        assert not a.flags != b.flags
