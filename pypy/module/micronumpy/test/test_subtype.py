from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest


class AppTestSupport(BaseNumpyAppTest):
    spaceconfig = dict(usemodules=["micronumpy", "struct", "binascii"])

    def setup_class(cls):
        BaseNumpyAppTest.setup_class.im_func(cls)
        cls.w_NoNew = cls.space.appexec([], '''():
            from numpypy import ndarray
            class NoNew(ndarray):
                def __new__(cls, subtype):
                    raise ValueError('should not call __new__')
                def __array_finalize__(self, obj):

                    self.called_finalize = True
            return NoNew ''')
        cls.w_SubType = cls.space.appexec([], '''():
            from numpypy import ndarray, array
            class SubType(ndarray):
                def __new__(obj, input_array):
                    obj = array(input_array, copy=False).view(obj)
                    obj.called_new = True
                    return obj
                def __array_finalize__(self, obj):
                    self.called_finalize = True
            return SubType ''')

    def test_subtype_base(self):
        from numpypy import ndarray, dtype
        class C(ndarray):
            def __new__(subtype, shape, dtype):
                self = ndarray.__new__(subtype, shape, dtype)
                self.id = 'subtype'
                return self
        a = C((), int)
        assert type(a) is C
        assert a.shape == ()
        assert a.dtype is dtype(int)
        assert a.id == 'subtype'
        a = C([2, 2], int)
        assert isinstance(a, C)
        assert isinstance(a, ndarray)
        assert a.shape == (2, 2)
        assert a.dtype is dtype(int)
        assert a.id == 'subtype'
        a = a.reshape(1, 4)
        b = a.reshape(4, 1)
        assert isinstance(b, C)
        #make sure __new__ was not called
        assert not getattr(b, 'id', None)
        a.fill(3)
        b = a[0]
        assert isinstance(b, C)
        assert (b == 3).all()
        b[0]=100
        assert a[0,0] == 100

        assert type(a) is not ndarray
        assert a[0,0] == 100
        assert a.base is not None
        b = a.__array__()
        assert type(b) is ndarray
        assert b[0,0] == 100
        assert b.base is a

    def test_subtype_view(self):
        from numpypy import ndarray, array
        class matrix(ndarray):
            def __new__(subtype, data, dtype=None, copy=True):
                if isinstance(data, matrix):
                    return data
                return data.view(subtype)
        a = array(range(5))
        b = matrix(a)
        assert isinstance(b, matrix)
        assert (b == a).all()
        a = array(5)[()]
        for s in [matrix, ndarray]:
            b = a.view(s)
            assert b == a
            assert type(b) is type(a)

    def test_subtype_like_matrix(self):
        import numpy as np
        arr = np.array([1,2,3])
        ret = np.ndarray.__new__(np.ndarray, arr.shape, arr.dtype, buffer=arr)
        assert (arr == ret).all()

    def test_finalize(self):
        #taken from http://docs.scipy.org/doc/numpy/user/basics.subclassing.html#simple-example-adding-an-extra-attribute-to-ndarray
        import numpypy as np
        class InfoArray(np.ndarray):
            def __new__(subtype, shape, dtype=float, buffer=None, offset=0,
                          strides=None, order='C', info=None):
                obj = np.ndarray.__new__(subtype, shape, dtype, buffer,
                         offset, strides, order)
                obj.info = info
                return obj

            def __array_finalize__(self, obj):
                if obj is None:
                    print 'finalize with None'
                    return
                # printing the object itself will crash the test
                print 'finalize with something',type(obj)
                self.info = getattr(obj, 'info', None)
        obj = InfoArray(shape=(3,))
        assert isinstance(obj, InfoArray)
        assert obj.info is None
        obj = InfoArray(shape=(3,), info='information')
        assert obj.info == 'information'
        v = obj[1:]
        assert isinstance(v, InfoArray)
        assert v.base is obj
        assert v.info == 'information'
        arr = np.arange(10)
        cast_arr = arr.view(InfoArray)
        assert isinstance(cast_arr, InfoArray)
        assert cast_arr.base is arr
        assert cast_arr.info is None

    def test_sub_where(self):
        from numpypy import where, ones, zeros, array
        a = array([1, 2, 3, 0, -3])
        v = a.view(self.NoNew)
        b = where(array(v) > 0, ones(5), zeros(5))
        assert (b == [1, 1, 1, 0, 0]).all()
        # where returns an ndarray irregardless of the subtype of v
        assert not isinstance(b, self.NoNew)

    def test_sub_repeat(self):
        from numpypy import array
        a = self.SubType(array([[1, 2], [3, 4]]))
        b = a.repeat(3)
        assert (b == [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4]).all()
        assert isinstance(b, self.SubType)

    def test_sub_flatiter(self):
        from numpypy import array
        a = array(range(9)).reshape(3, 3).view(self.NoNew)
        c = array(range(9)).reshape(3, 3)
        assert isinstance(a.flat[:] + a.flat[:], self.NoNew)
        assert isinstance(a.flat[:] + c.flat[:], self.NoNew)
        assert isinstance(c.flat[:] + a.flat[:], self.NoNew)
        assert not isinstance(c.flat[:] + c.flat[:], self.NoNew)

    def test_sub_getitem_filter(self):
        from numpypy import array
        a = array(range(5))
        b = self.SubType(a)
        c = b[array([False, True, False, True, False])]
        assert c.shape == (2,)
        assert (c == [1, 3]).all()
        assert isinstance(c, self.SubType)
        assert b.called_new
        assert not getattr(c, 'called_new', False)
        assert c.called_finalize

    def test_sub_getitem_array_int(self):
        from numpypy import array
        a = array(range(5))
        b = self.SubType(a)
        assert b.called_new
        c = b[array([3, 2, 1, 4])]
        assert (c == [3, 2, 1, 4]).all()
        assert isinstance(c, self.SubType)
        assert not getattr(c, 'called_new', False)
        assert c.called_finalize

    def test_sub_round(self):
        from numpypy import array
        a = array(range(10), dtype=float).view(self.NoNew)
        # numpy compatibility
        b = a.round(decimals=0)
        assert isinstance(b, self.NoNew)
        b = a.round(decimals=1)
        assert not isinstance(b, self.NoNew)
        b = a.round(decimals=-1)
        assert not isinstance(b, self.NoNew)

    def test_sub_dot(self):
        # the returned type is that of the first argument
        from numpypy import array
        a = array(range(12)).reshape(3,4)
        b = self.SubType(a)
        c = array(range(12)).reshape(4,3).view(self.SubType)
        d = c.dot(a)
        assert isinstance(d, self.SubType)
        assert not getattr(d, 'called_new', False)
        assert d.called_finalize
        d = a.dot(c)
        assert not isinstance(d, self.SubType)
        assert not getattr(d, 'called_new', False)
        assert not getattr(d, 'called_finalize', False)

    def test_sub_reduce(self):
        # i.e. sum, max
        # test for out as well
        from numpypy import array
        a = array(range(12)).reshape(3,4)
        b = self.SubType(a)
        c = b.sum(axis=0)
        assert (c == [12, 15, 18, 21]).all()
        assert isinstance(c, self.SubType)
        assert not getattr(c, 'called_new', False)
        assert c.called_finalize
        d = array(range(4))
        c = b.sum(axis=0, out=d)
        assert c is d
        assert not isinstance(c, self.SubType)
        d = array(range(4)).view(self.NoNew)
        c = b.sum(axis=0, out=d)
        assert c is d
        assert isinstance(c, self.NoNew)

    def test_sub_call2(self):
        # c + a vs. a + c, what about array priority?
        from numpypy import array
        a = array(range(12)).view(self.NoNew)
        b = self.SubType(range(12))
        c = b + a
        assert isinstance(c, self.SubType)
        c = a + b
        assert isinstance(c, self.NoNew)
        d = range(12)
        e = a - d
        assert isinstance(e, self.NoNew)

    def test_sub_call1(self):
        from numpypy import array, sqrt
        a = array(range(12)).view(self.NoNew)
        b = sqrt(a)
        assert b.called_finalize == True

    def test_sub_astype(self):
        from numpypy import array
        a = array(range(12)).view(self.NoNew)
        b = a.astype(float)
        assert b.called_finalize == True

    def test_sub_reshape(self):
        from numpypy import array
        a = array(range(12)).view(self.NoNew)
        b = a.reshape(3, 4)
        assert b.called_finalize == True

    def test___array__(self):
        import sys
        from numpypy import ndarray, array, dtype
        class D(ndarray):
            def __new__(subtype, shape, dtype):
                self = ndarray.__new__(subtype, shape, dtype)
                self.id = 'subtype'
                return self
        class C(object):
            def __init__(self, val, dtype):
                self.val = val
                self.dtype = dtype
            def __array__(self, dtype=None):
                retVal = D(self.val, dtype)
                return retVal

        a = C([2, 2], int)
        b = array(a)
        assert b.shape == (2, 2)
        if '__pypy__' in sys.builtin_module_names:
            assert b.id == 'subtype'
            assert isinstance(b, D)
        c = array(a, float)
        assert c.dtype is dtype(float)

    def test__getitem_modifies_shape(self):
        import numpypy as N
        # numpy's matrix class caused an infinite loop
        class matrix(N.ndarray):
            getcnt = 0
            def __new__(subtype, data, dtype=None, copy=True):
                arr = N.array(data, dtype=dtype, copy=copy)
                shape = arr.shape

                ret = N.ndarray.__new__(subtype, shape, arr.dtype,
                                        buffer=arr,
                                        order=True)
                return ret

            def __getitem__(self, index):
                matrix.getcnt += 1
                if matrix.getcnt > 10:
                    # XXX strides.find_shape_and_elems is sensitive
                    # to shape modification
                    xxx
                out = N.ndarray.__getitem__(self, index)

                if not isinstance(out, N.ndarray):
                    return out
                    # Determine when we should have a column array
                old_shape = out.shape
                if out.ndim < 2:
                    sh = out.shape[0]
                    try:
                        n = len(index)
                    except:
                        n = 0
                    if n > 1:
                        out.shape = (sh, 1)
                    else:
                        out.shape = (1, sh)
                print 'out, shape was',old_shape,'now',out.shape
                return out
        a = matrix([[1., 2.]])
        b = N.array([a])

    def test_setstate_no_version(self):
        # Some subclasses of ndarray, like MaskedArray, do not use
        # version in __setstare__
        from numpy import ndarray, array
        from pickle import loads, dumps
        import sys, new
        class D(ndarray):
            ''' A subtype with a constructor that accepts a list of
                data values, where ndarray accepts a shape
            '''
            def __new__(subtype, data, dtype=None, copy=True):
                arr = array(data, dtype=dtype, copy=copy)
                shape = arr.shape
                ret = ndarray.__new__(subtype, shape, arr.dtype,
                                        buffer=arr,
                                        order=True)
                return ret
            def __setstate__(self, state):
                (version, shp, typ, isf, raw) = state
                ndarray.__setstate__(self, (shp, typ, isf, raw))

        D.__module__ = 'mod'
        mod = new.module('mod')
        mod.D = D
        sys.modules['mod'] = mod
        a = D([1., 2.])
        s = dumps(a)
        #Taken from numpy version 1.8
        s_from_numpy = '''ignore this line
            _reconstruct
            p0
            (cmod
            D
            p1
            (I0
            tp2
            S'b'
            p3
            tp4
            Rp5
            (I1
            (I2
            tp6
            cnumpy
            dtype
            p7
            (S'f8'
            p8
            I0
            I1
            tp9
            Rp10
            (I3
            S'<'
            p11
            NNNI-1
            I-1
            I0
            tp12
            bI00
            S'\x00\x00\x00\x00\x00\x00\xf0?\x00\x00\x00\x00\x00\x00\x00@'
            p13
            tp14
            b.'''.replace('            ','')
        for ss,sn in zip(s.split('\n')[1:],s_from_numpy.split('\n')[1:]):
            if len(ss)>10:
                # ignore binary data, it will be checked later
                continue
            assert ss == sn
        b = loads(s)
        assert (a == b).all()
        assert isinstance(b, D)
