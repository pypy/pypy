from pypy.module.test_lib_pypy.numpypy.test_base import BaseNumpyAppTest

class AppTestTwoDimBase(BaseNumpyAppTest):
    def test_eye(self):
        from numpypy import eye, int32, dtype
        a = eye(0)
        assert len(a) == 0
        assert a.dtype == dtype('float64')
        assert a.shape == (0, 0)
        b = eye(1, dtype=int32)
        assert len(b) == 1
        assert b[0][0] == 1
        assert b.shape == (1, 1)
        assert b.dtype == dtype('int32')
        c = eye(2)
        assert c.shape == (2, 2)
        assert (c == [[1, 0], [0, 1]]).all()
        d = eye(3, dtype='int32')
        assert d.shape == (3, 3)
        assert d.dtype == dtype('int32')
        assert (d == [[1, 0, 0], [0, 1, 0], [0, 0, 1]]).all()
        e = eye(3, 4)
        assert e.shape == (3, 4)
        assert (e == [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]).all()
        f = eye(2, 4, k=3)
        assert f.shape == (2, 4)
        assert (f == [[0, 0, 0, 1], [0, 0, 0, 0]]).all()
        g = eye(3, 4, k=-1)
        assert g.shape == (3, 4)
        assert (g == [[0, 0, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0]]).all()
