from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestSupport(BaseNumpyAppTest):
    def setup_class(cls):
        import struct
        BaseNumpyAppTest.setup_class.im_func(cls)
        cls.w_data = cls.space.wrap(struct.pack('dddd', 1, 2, 3, 4))
        cls.w_fdata = cls.space.wrap(struct.pack('f', 2.3))
        cls.w_float16val = cls.space.wrap('\x00E') # 5.0 in float16
        cls.w_float32val = cls.space.wrap(struct.pack('f', 5.2))
        cls.w_float64val = cls.space.wrap(struct.pack('d', 300.4))
        cls.w_ulongval = cls.space.wrap(struct.pack('L', 12))

    def test_argsort_dtypes(self):
        from numpypy import array, arange
        assert array(2.0).argsort() == 0
        nnp = self.non_native_prefix
        for dtype in ['int', 'float', 'int16', 'float32', 'uint64',
                        nnp + 'i2', complex]:
            a = array([6, 4, -1, 3, 8, 3, 256+20, 100, 101], dtype=dtype)
            c = a.copy()
            res = a.argsort()
            assert (res == [2, 3, 5, 1, 0, 4, 7, 8, 6]).all(), \
                'a,res,dtype %r,%r,%r' % (a,res,dtype)
            assert (a == c).all() # not modified
            a = arange(100)
            assert (a.argsort() == a).all()
        raises(NotImplementedError, 'arange(10,dtype="float16").argsort()')

    def test_argsort_nd(self):
        from numpypy import array
        a = array([[4, 2], [1, 3]])
        assert (a.argsort() == [[1, 0], [0, 1]]).all()
        a = array(range(10) + range(10) + range(10))
        b = a.argsort()
        assert (b[:3] == [0, 10, 20]).all()
        #trigger timsort 'run' mode which calls arg_getitem_slice
        a = array(range(100) + range(100) + range(100))
        b = a.argsort()
        assert (b[:3] == [0, 100, 200]).all()
        a = array([[[]]]).reshape(3,4,0)
        b = a.argsort()
        assert b.size == 0

    def test_argsort_random(self):
        from numpypy import array
        from _random import Random
        rnd = Random(1)
        a = array([rnd.random() for i in range(512*2)]).reshape(512,2)
        a.argsort()

    def test_argsort_axis(self):
        from numpypy import array
        a = array([[4, 2], [1, 3]])
        assert (a.argsort(axis=None) == [2, 1, 3, 0]).all()
        assert (a.argsort(axis=-1) == [[1, 0], [0, 1]]).all()
        assert (a.argsort(axis=0) == [[1, 0], [0, 1]]).all()
        assert (a.argsort(axis=1) == [[1, 0], [0, 1]]).all()
        a = array([[3, 2, 1], [1, 2, 3]])
        assert (a.argsort(axis=0) == [[1, 0, 0], [0, 1, 1]]).all()
        assert (a.argsort(axis=1) == [[2, 1, 0], [0, 1, 2]]).all()

    def test_sort_dtypes(self):
        from numpypy import array, arange
        nnp = self.non_native_prefix
        for dtype in ['int', 'float', 'int16', 'float32', 'uint64',
                        nnp + 'i2', complex]:
            a = array([6, 4, -1, 3, 8, 3, 256+20, 100, 101], dtype=dtype)
            c = a.copy()
            a.sort()
            assert (a == [-1, 3, 3, 4, 6, 8, 100, 101, 256+20]).all(), \
                'a,orig,dtype %r,%r,%r' % (a,c,dtype)
            a = arange(100)
            c = a.copy()
            assert (a.sort() == c).all()


# tests from numpy/tests/test_multiarray.py
    def test_sort_corner_cases(self):
        # test ordering for floats and complex containing nans. It is only
        # necessary to check the lessthan comparison, so sorts that
        # only follow the insertion sort path are sufficient. We only
        # test doubles and complex doubles as the logic is the same.

        # check doubles
        from numpypy import array, nan, zeros, complex128, arange, dtype
        from numpy import isnan
        a = array([nan, 1, 0])
        b = a.copy()
        b.sort()
        assert (isnan(b) == isnan(a[::-1])).all()
        assert (b[:2] == a[::-1][:2]).all()

        # check complex
        a = zeros(9, dtype=complex128)
        a.real += [nan, nan, nan, 1, 0, 1, 1, 0, 0]
        a.imag += [nan, 1, 0, nan, nan, 1, 0, 1, 0]
        b = a.copy()
        b.sort()
        assert (isnan(b) == isnan(a[::-1])).all()
        assert (b[:4] == a[::-1][:4]).all()

        # all c scalar sorts use the same code with different types
        # so it suffices to run a quick check with one type. The number
        # of sorted items must be greater than ~50 to check the actual
        # algorithm because quick and merge sort fall over to insertion
        # sort for small arrays.
        a = arange(101)
        b = a[::-1].copy()
        for kind in ['q', 'm', 'h'] :
            msg = "scalar sort, kind=%s" % kind
            c = a.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg
            c = b.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg

        # test complex sorts. These use the same code as the scalars
        # but the compare fuction differs.
        ai = a*1j + 1
        bi = b*1j + 1
        for kind in ['q', 'm', 'h'] :
            msg = "complex sort, real part == 1, kind=%s" % kind
            c = ai.copy();
            c.sort(kind=kind)
            assert (c == ai).all(), msg
            c = bi.copy();
            c.sort(kind=kind)
            assert (c == ai).all(), msg
        ai = a + 1j
        bi = b + 1j
        for kind in ['q', 'm', 'h'] :
            msg = "complex sort, imag part == 1, kind=%s" % kind
            c = ai.copy();
            c.sort(kind=kind)
            assert (c == ai).all(), msg
            c = bi.copy();
            c.sort(kind=kind)
            assert (c == ai).all(), msg

        # test string sorts.
        s = 'aaaaaaaa'
        a = array([s + chr(i) for i in range(101)])
        b = a[::-1].copy()
        for kind in ['q', 'm', 'h'] :
            msg = "string sort, kind=%s" % kind
            c = a.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg
            c = b.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg

        # check axis handling. This should be the same for all type
        # specific sorts, so we only check it for one type and one kind
        a = array([[3, 2], [1, 0]])
        b = array([[1, 0], [3, 2]])
        c = array([[2, 3], [0, 1]])
        d = a.copy()
        d.sort(axis=0)
        assert (d == b).all(), "test sort with axis=0"
        d = a.copy()
        d.sort(axis=1)
        assert (d == c).all(), "test sort with axis=1"
        d = a.copy()
        d.sort()
        assert (d == c).all(), "test sort with default axis"


        # test record array sorts.
        dt =dtype([('f', float), ('i', int)])
        a = array([(i, i) for i in range(101)], dtype = dt)
        b = a[::-1]
        for kind in ['q', 'h', 'm'] :
            msg = "object sort, kind=%s" % kind
            c = a.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg
            c = b.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg

    def test_sort_unicode(self):
        from numpypy import array
        # test unicode sorts.
        s = 'aaaaaaaa'
        try:
            a = array([s + chr(i) for i in range(101)], dtype=unicode)
            b = a[::-1].copy()
        except:
            skip('unicode type not supported yet')
        for kind in ['q', 'm', 'h'] :
            msg = "unicode sort, kind=%s" % kind
            c = a.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg
            c = b.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg

    def test_sort_objects(self):
        # test object array sorts.
        from numpypy import empty
        try:
            a = empty((101,), dtype=object)
        except:
            skip('object type not supported yet')
        a[:] = list(range(101))
        b = a[::-1]
        for kind in ['q', 'h', 'm'] :
            msg = "object sort, kind=%s" % kind
            c = a.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg
            c = b.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg

    def test_sort_datetime(self):
        from numpypy import arange
        # test datetime64 sorts.
        try:
            a = arange(0, 101, dtype='datetime64[D]')
        except:
            skip('datetime type not supported yet')
        b = a[::-1]
        for kind in ['q', 'h', 'm'] :
            msg = "datetime64 sort, kind=%s" % kind
            c = a.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg
            c = b.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg

        # test timedelta64 sorts.
        a = arange(0, 101, dtype='timedelta64[D]')
        b = a[::-1]
        for kind in ['q', 'h', 'm'] :
            msg = "timedelta64 sort, kind=%s" % kind
            c = a.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg
            c = b.copy();
            c.sort(kind=kind)
            assert (c == a).all(), msg

    def test_sort_order(self):
        from numpypy import array, zeros
        from sys import byteorder
        # Test sorting an array with fields
        x1 = array([21, 32, 14])
        x2 = array(['my', 'first', 'name'])
        x3=array([3.1, 4.5, 6.2])
        r=zeros(3, dtype=[('id','i'),('word','S5'),('number','f')])
        r['id'] = x1
        r['word'] = x2
        r['number'] = x3

        r.sort(order=['id'])
        assert (r['id'] == [14, 21, 32]).all()
        assert (r['word'] == ['name', 'my', 'first']).all()
        assert max(abs(r['number'] - [6.2, 3.1, 4.5])) < 1e-6

        r.sort(order=['word'])
        assert (r['id'] == [32, 21, 14]).all()
        assert (r['word'] == ['first', 'my', 'name']).all()
        assert max(abs(r['number'] - [4.5, 3.1, 6.2])) < 1e-6

        r.sort(order=['number'])
        assert (r['id'] == [21, 32, 14]).all()
        assert (r['word'] == ['my', 'first', 'name']).all()
        assert max(abs(r['number'] - [3.1, 4.5, 6.2])) < 1e-6

        if byteorder == 'little':
            strtype = '>i2'
        else:
            strtype = '<i2'
        mydtype = [('name', 'S5'), ('col2', strtype)]
        r = array([('a', 1), ('b', 255), ('c', 3), ('d', 258)],
                     dtype= mydtype)
        r.sort(order='col2')
        assert (r['col2'] == [1, 3, 255, 258]).all()
        assert (r == array([('a', 1), ('c', 3), ('b', 255), ('d', 258)],
                                 dtype=mydtype)).all()




# tests from numpy/tests/test_regression.py
    def test_sort_bigendian(self):
        from numpypy import array, dtype
        a = array(range(11),dtype='float64')
        c = a.astype(dtype('<f8'))
        c.sort()
        assert max(abs(a-c)) < 1e-32

    def test_string_sort_with_zeros(self):
        from numpypy import fromstring
        """Check sort for strings containing zeros."""
        x = fromstring("\x00\x02\x00\x01", dtype="S2")
        y = fromstring("\x00\x01\x00\x02", dtype="S2")
        x.sort(kind='q')
        assert (x == y).all()
