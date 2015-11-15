import py
import sys

from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestDeprecations(BaseNumpyAppTest):
    spaceconfig = dict(usemodules=["micronumpy", "struct", "binascii"])

    def test_getitem(self):
        import numpy as np
        import warnings
        warnings.simplefilter('error', np.VisibleDeprecationWarning)
        try:
            arr = np.ones((5, 4, 3))
            index = np.array([True])
            #self.assert_deprecated(arr.__getitem__, args=(index,))
            raises(np.VisibleDeprecationWarning, arr.__getitem__, index)

            index = np.array([False] * 6)
            #self.assert_deprecated(arr.__getitem__, args=(index,))
            raises(np.VisibleDeprecationWarning, arr.__getitem__, index)

            index = np.zeros((4, 4), dtype=bool)
            #self.assert_deprecated(arr.__getitem__, args=(index,))
            raises(np.VisibleDeprecationWarning, arr.__getitem__, index)
            #self.assert_deprecated(arr.__getitem__, args=((slice(None), index),))
            raises(np.VisibleDeprecationWarning, arr.__getitem__, (slice(None), index))
        finally:
            warnings.simplefilter('default', np.VisibleDeprecationWarning)

