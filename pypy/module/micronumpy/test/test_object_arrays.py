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
        raises(TypeError, np.add, a, 1)
        res = a + b
        assert res[0] == "foobar"

    def test_bool_func(self):
        import numpy as np
        a = np.array(["foo"], dtype=object)
        b = a and complex(1, -1)
        assert b == complex(1, -1)
        b = np.array(complex(1, -1)) and a
        assert (b == a).all()

    def test_logical_ufunc(self):
        import numpy as np
        a = np.array(["foo"], dtype=object)
        b = np.array([1], dtype=object)
        d = np.array([complex(1, 10)], dtype=object)
        c = np.logical_and(a, 1)
        assert c.dtype == np.dtype('object')
        assert c == 1
        c = np.logical_and(b, complex(1, -1))
        assert c.dtype == np.dtype('object')
        assert c == complex(1, -1)
        c = np.logical_and(d, b)
        assert c == 1
        c = b & 1
        assert c.dtype == np.dtype('object')
        assert (c == 1).all()
        c = np.array(1) & b
        assert (c == b).all()

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

    def test_complex_op(self):
        import numpy as np
        a = np.array(['abc', 'def'], dtype=object) 
        b = np.array([1, 2, 3], dtype=object) 
        c = np.array([complex(1, 1), complex(1, -1)], dtype=object)
        for arg in (a,b,c):
            assert (arg == np.real(arg)).all()
            assert (0 == np.imag(arg)).all()
        raises(AttributeError, np.conj, a)
        res = np.conj(b)
        assert (res == b).all()
        res = np.conj(c)
        assert res[0] == c[1] and res[1] == c[0]

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

    def test_array_interface(self):
        import numpy as np
        class DummyArray(object):
            def __init__(self, interface, base=None):
                self.__array_interface__ = interface
                self.base = base
        a = np.array([(1, 2, 3)], dtype='u4,u4,u4')
        b = np.array([(1, 2, 3), (4, 5, 6), (7, 8, 9)], dtype='u4,u4,u4')
        interface = dict(a.__array_interface__)
        interface['shape'] = tuple([3])
        interface['strides'] = tuple([0])
        c = np.array(DummyArray(interface, base=a))
        assert (c == np.array([(1, 2, 3), (1, 2, 3), (1, 2, 3)], dtype='u4,u4,u4') ).all()
