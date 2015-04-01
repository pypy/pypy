from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestObjectDtypes(BaseNumpyAppTest):
    def test_scalar_from_object(self):
        from numpy import array
        import sys
        class Polynomial(object):
            def whatami(self):
                return 'an object'
        a = array(Polynomial())
        assert a.shape == ()
        assert a.sum().whatami() == 'an object'

    def test_uninitialized_object_array_is_filled_by_None(self):
        import numpy as np

        a = np.ndarray([5], dtype="O")

        assert a[0] == None

    def test_object_arrays_add(self):
        import numpy as np

        a = np.array(["foo"], dtype=object)
        b = np.array(["bar"], dtype=object)

        res = a + b
        assert res[0] == "foobar"

    def test_reduce(self):
        import numpy as np
        class O(object):
            def whatami(self):
                return 'an object'
        fiveOs = [O()] * 5
        a = np.array(fiveOs, dtype=object)
        print np.maximum
        b = np.maximum.reduce(a)
        assert b is not None

    def test_keep_object_alive(self):
        # only translated does it really test the gc
        import numpy as np
        import gc
        class O(object):
            def whatami(self):
                return 'an object'
        fiveOs = [O()] * 5
        a = np.array(fiveOs, dtype=object)
        del fiveOs
        gc.collect()
        assert a[2].whatami() == 'an object'
