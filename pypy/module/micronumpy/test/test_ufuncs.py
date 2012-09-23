
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest
from math import isnan, isinf, copysign
from sys import version_info, builtin_module_names
from pypy.rlib.rcomplex import c_pow

from pypy.conftest import option

def rAlmostEqual(a, b, rel_err = 2e-15, abs_err = 5e-323, msg='', isnumpy=False):
    """Fail if the two floating-point numbers are not almost equal.

    Determine whether floating-point values a and b are equal to within
    a (small) rounding error.  The default values for rel_err and
    abs_err are chosen to be suitable for platforms where a float is
    represented by an IEEE 754 double.  They allow an error of between
    9 and 19 ulps.
    """

    # special values testing
    if isnan(a):
        if isnan(b):
            return True,''
        raise AssertionError(msg + '%r should be nan' % (b,))

    if isinf(a):
        if a == b:
            return True,''
        raise AssertionError(msg + 'finite result where infinity expected: '+ \
                          'expected %r, got %r' % (a, b))

    # if both a and b are zero, check whether they have the same sign
    # (in theory there are examples where it would be legitimate for a
    # and b to have opposite signs; in practice these hardly ever
    # occur).
    if not a and not b and not isnumpy:
        # only check it if we are running on top of CPython >= 2.6
        if version_info >= (2, 6) and copysign(1., a) != copysign(1., b):
            raise AssertionError( msg + \
                    'zero has wrong sign: expected %r, got %r' % (a, b))

    # if a-b overflows, or b is infinite, return False.  Again, in
    # theory there are examples where a is within a few ulps of the
    # max representable float, and then b could legitimately be
    # infinite.  In practice these examples are rare.
    try:
        absolute_error = abs(b-a)
    except OverflowError:
        pass
    else:
        # test passes if either the absolute error or the relative
        # error is sufficiently small.  The defaults amount to an
        # error of between 9 ulps and 19 ulps on an IEEE-754 compliant
        # machine.
        if absolute_error <= max(abs_err, rel_err * abs(a)):
            return True,''
    raise AssertionError(msg + \
            '%r and %r are not sufficiently close, %g > %g' %\
            (a, b, absolute_error, max(abs_err, rel_err*abs(a))))

class AppTestUfuncs(BaseNumpyAppTest):
    def setup_class(cls):
        import os
        BaseNumpyAppTest.setup_class.im_func(cls)
        fname128 = os.path.join(os.path.dirname(__file__), 'complex_testcases.txt')
        fname64 = os.path.join(os.path.dirname(__file__), 'complex64_testcases.txt')
        cls.w_testcases128 = cls.space.wrap(fname128)
        cls.w_testcases64 = cls.space.wrap(fname64)
        def cls_c_pow(self, *args):
            return c_pow(*args)
        cls.w_c_pow = cls.space.wrap(cls_c_pow)
        cls.w_runAppDirect = cls.space.wrap(option.runappdirect)
        cls.w_isWindows = cls.space.wrap(os.name == 'nt')
        def cls_rAlmostEqual(self, *args, **kwargs):
            if '__pypy__' not in builtin_module_names:
                kwargs['isnumpy'] = True
            return rAlmostEqual(*args, **kwargs)
        cls.w_rAlmostEqual = cls.space.wrap(cls_rAlmostEqual)


    def test_ufunc_instance(self):
        from _numpypy import add, ufunc

        assert isinstance(add, ufunc)
        assert repr(add) == "<ufunc 'add'>"
        assert repr(ufunc) == "<type 'numpypy.ufunc'>" or repr(ufunc) == "<type 'numpy.ufunc'>"

    def test_ufunc_attrs(self):
        from _numpypy import add, multiply, sin

        assert add.identity == 0
        assert multiply.identity == 1
        assert sin.identity is None

        assert add.nin == 2
        assert multiply.nin == 2
        assert sin.nin == 1

    def test_wrong_arguments(self):
        from _numpypy import add, sin

        raises(ValueError, add, 1)
        raises(TypeError, add, 1, 2, 3)
        raises(TypeError, sin, 1, 2)
        raises(ValueError, sin)

    def test_single_item(self):
        from _numpypy import negative, sign, minimum

        assert negative(5.0) == -5.0
        assert sign(-0.0) == 0.0
        assert minimum(2.0, 3.0) == 2.0

    def test_sequence(self):
        from _numpypy import array, ndarray, negative, minimum
        a = array(range(3))
        b = [2.0, 1.0, 0.0]
        c = 1.0
        b_neg = negative(b)
        assert isinstance(b_neg, ndarray)
        for i in range(3):
            assert b_neg[i] == -b[i]
        min_a_b = minimum(a, b)
        assert isinstance(min_a_b, ndarray)
        for i in range(3):
            assert min_a_b[i] == min(a[i], b[i])
        min_b_a = minimum(b, a)
        assert isinstance(min_b_a, ndarray)
        for i in range(3):
            assert min_b_a[i] == min(a[i], b[i])
        min_a_c = minimum(a, c)
        assert isinstance(min_a_c, ndarray)
        for i in range(3):
            assert min_a_c[i] == min(a[i], c)
        min_c_a = minimum(c, a)
        assert isinstance(min_c_a, ndarray)
        for i in range(3):
            assert min_c_a[i] == min(a[i], c)
        min_b_c = minimum(b, c)
        assert isinstance(min_b_c, ndarray)
        for i in range(3):
            assert min_b_c[i] == min(b[i], c)
        min_c_b = minimum(c, b)
        assert isinstance(min_c_b, ndarray)
        for i in range(3):
            assert min_c_b[i] == min(b[i], c)

    def test_negative(self):
        from _numpypy import array, negative

        a = array([-5.0, 0.0, 1.0])
        b = negative(a)
        for i in range(3):
            assert b[i] == -a[i]

        a = array([-5.0, 1.0])
        b = negative(a)
        a[0] = 5.0
        assert b[0] == 5.0
        a = array(range(30))
        assert negative(a + a)[3] == -6

    def test_abs(self):
        from _numpypy import array, absolute

        a = array([-5.0, -0.0, 1.0])
        b = absolute(a)
        for i in range(3):
            assert b[i] == abs(a[i])

    def test_add(self):
        from _numpypy import array, add

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = add(a, b)
        for i in range(3):
            assert c[i] == a[i] + b[i]

    def test_divide(self):
        from _numpypy import array, divide

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = divide(a, b)
        for i in range(3):
            assert c[i] == a[i] / b[i]

        assert (divide(array([-10]), array([2])) == array([-5])).all()

    def test_true_divide(self):
        import math
        from _numpypy import array, true_divide
        import math

        a = array([0, 1, 2, 3, 4, 1, -1])
        b = array([4, 4, 4, 4, 4, 0,  0])
        c = true_divide(a, b)
        assert (c == [0.0, 0.25, 0.5, 0.75, 1.0, float('inf'), float('-inf')]).all()

        assert math.isnan(true_divide(0, 0))

    def test_fabs(self):
        from _numpypy import array, fabs, complex128
        from math import fabs as math_fabs, isnan

        a = array([-5.0, -0.0, 1.0])
        b = fabs(a)
        for i in range(3):
            assert b[i] == math_fabs(a[i])
        assert fabs(float('inf')) == float('inf')
        assert fabs(float('-inf')) == float('inf')
        assert isnan(fabs(float('nan')))

        a = complex128(complex(-5., 5.))
        raises(TypeError, fabs, a)


    def test_fmax(self):
        from _numpypy import fmax, array
        import math

        nnan, nan, inf, ninf = float('-nan'), float('nan'), float('inf'), float('-inf')

        a = [ninf, -5, 0, 5, inf]
        assert (fmax(a, [ninf]*5) == a).all()
        assert (fmax(a, [inf]*5) == [inf]*5).all()
        assert (fmax(a, [1]*5) == [1, 1, 1, 5, inf]).all()
        assert fmax(nan, 0) == 0
        assert fmax(0, nan) == 0
        assert math.isnan(fmax(nan, nan))
        # The numpy docs specify that the FIRST NaN should be used if both are NaN
        # Since comparisons with nnan and nan all return false,
        # use copysign on both sides to sidestep bug in nan representaion
        # on Microsoft win32
        assert math.copysign(1., fmax(nnan, nan)) == math.copysign(1., nnan)

        a = array((complex(ninf, 10), complex(10, ninf), 
                   complex( inf, 10), complex(10,  inf),
                   5+5j, 5-5j, -5+5j, -5-5j,
                   0+5j, 0-5j, 5, -5,
                   complex(nan, 0), complex(0, nan)), dtype = complex)
        b = [ninf]*a.size
        res = [a[0 ], a[1 ], a[2 ], a[3 ], 
               a[4 ], a[5 ], a[6 ], a[7 ],
               a[8 ], a[9 ], a[10], a[11],
               b[12], b[13]]
        r2 = fmax(a,b)
        r3 = (r2 == res)
        assert (fmax(a, b) == res).all()
        b = [inf]*a.size
        res = [b[0 ], b[1 ], a[2 ], b[3 ], 
               b[4 ], b[5 ], b[6 ], b[7 ],
               b[8 ], b[9 ], b[10], b[11],
               b[12], b[13]]
        assert (fmax(a, b) == res).all()
        b = [0]*a.size
        res = [b[0 ], a[1 ], a[2 ], a[3 ], 
               a[4 ], a[5 ], b[6 ], b[7 ],
               a[8 ], b[9 ], a[10], b[11],
               b[12], b[13]]
        assert (fmax(a, b) == res).all()


    def test_fmin(self):
        from _numpypy import fmin, array
        import math

        nnan, nan, inf, ninf = float('-nan'), float('nan'), float('inf'), float('-inf')

        a = [ninf, -5, 0, 5, inf]
        assert (fmin(a, [ninf]*5) == [ninf]*5).all()
        assert (fmin(a, [inf]*5) == a).all()
        assert (fmin(a, [1]*5) == [ninf, -5, 0, 1, 1]).all()
        assert fmin(nan, 0) == 0
        assert fmin(0, nan) == 0
        assert math.isnan(fmin(nan, nan))
        # The numpy docs specify that the FIRST NaN should be used if both are NaN
        # use copysign on both sides to sidestep bug in nan representaion
        # on Microsoft win32
        assert math.copysign(1., fmin(nnan, nan)) == math.copysign(1., nnan)

        a = array((complex(ninf, 10), complex(10, ninf), 
                   complex( inf, 10), complex(10,  inf),
                   5+5j, 5-5j, -5+5j, -5-5j,
                   0+5j, 0-5j, 5, -5,
                   complex(nan, 0), complex(0, nan)), dtype = complex)
        b = [inf]*a.size
        res = [a[0 ], a[1 ], b[2 ], a[3 ], 
               a[4 ], a[5 ], a[6 ], a[7 ],
               a[8 ], a[9 ], a[10], a[11],
               b[12], b[13]]
        assert (fmin(a, b) == res).all()
        b = [ninf]*a.size
        res = [b[0 ], b[1 ], b[2 ], b[3 ], 
               b[4 ], b[5 ], b[6 ], b[7 ],
               b[8 ], b[9 ], b[10], b[11],
               b[12], b[13]]
        assert (fmin(a, b) == res).all()
        b = [0]*a.size
        res = [a[0 ], b[1 ], b[2 ], b[3 ], 
               b[4 ], b[5 ], a[6 ], a[7 ],
               b[8 ], a[9 ], b[10], a[11],
               b[12], b[13]]
        assert (fmin(a, b) == res).all()


    def test_fmod(self):
        from _numpypy import fmod
        import math

        assert fmod(-1e-100, 1e100) == -1e-100
        assert fmod(3, float('inf')) == 3
        assert (fmod([-3, -2, -1, 1, 2, 3], 2) == [-1,  0, -1,  1,  0,  1]).all()
        for v in [float('inf'), float('-inf'), float('nan'), float('-nan')]:
            assert math.isnan(fmod(v, 2))

    def test_minimum(self):
        from _numpypy import array, minimum

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = minimum(a, b)
        for i in range(3):
            assert c[i] == min(a[i], b[i])

    def test_maximum(self):
        from _numpypy import array, maximum

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = maximum(a, b)
        for i in range(3):
            assert c[i] == max(a[i], b[i])

        x = maximum(2, 3)
        assert x == 3
        assert isinstance(x, (int, long))

    def test_multiply(self):
        from _numpypy import array, multiply

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = multiply(a, b)
        for i in range(3):
            assert c[i] == a[i] * b[i]

    def test_sign(self):
        from _numpypy import array, sign, dtype

        reference = [-1.0, 0.0, 0.0, 1.0]
        a = array([-5.0, -0.0, 0.0, 6.0])
        b = sign(a)
        for i in range(4):
            assert b[i] == reference[i]

        a = sign(array(range(-5, 5)))
        ref = [-1, -1, -1, -1, -1, 0, 1, 1, 1, 1]
        for i in range(10):
            assert a[i] == ref[i]

        a = sign(array([10+10j, -10+10j, 0+10j, 0-10j, 0+0j, 0-0j], dtype=complex))
        ref = [1, -1, 1, -1, 0, 0]
        assert (a == ref).all()

    def test_signbit(self):
        from _numpypy import signbit

        assert (signbit([0, 0.0, 1, 1.0, float('inf')]) ==
            [False, False, False, False, False]).all()
        assert (signbit([-0, -0.0, -1, -1.0, float('-inf')]) ==
            [False,  True,  True,  True,  True]).all()

        raises(TypeError, signbit, complex(1,1))

        skip('sign of nan is non-determinant')
        assert (signbit([float('nan'), float('-nan'), -float('nan')]) ==
            [False, True, True]).all()    

    def test_reciprocal(self):
        from _numpypy import array, reciprocal, complex64, complex128

        inf = float('inf')
        nan = float('nan')
        reference = [-0.2, inf, -inf, 2.0, nan]
        a = array([-5.0, 0.0, -0.0, 0.5, nan])
        b = reciprocal(a)
        for i in range(4):
            assert b[i] == reference[i]

        #complex    
        orig = [2.+4.j, -2.+4.j, 2.-4.j, -2.-4.j, 
                complex(inf, 3), complex(inf, -3), complex(inf, -inf), 
                complex(nan, 3), 0+0j, 0-0j]
        a2 = 2.**2 + 4.**2
        r = 2. / a2
        i = 4. / a2
        cnan = complex(nan, nan)
        expected = [complex(r, -i), complex(-r, -i), complex(r, i), 
                    complex(-r, i), 
                    -0j, 0j, cnan, 
                    cnan, cnan, cnan]
        for c, rel_err in ((complex64, 2e-7), (complex128, 2e-15), ):
            actual = reciprocal(array([orig], dtype=c))
            for b, a, e in zip(orig, actual, expected):
                assert (a[0].real - e.real) < rel_err
                assert (a[0].imag - e.imag) < rel_err

    def test_subtract(self):
        from _numpypy import array, subtract

        a = array([-5.0, -0.0, 1.0])
        b = array([ 3.0, -2.0,-3.0])
        c = subtract(a, b)
        for i in range(3):
            assert c[i] == a[i] - b[i]

    def test_floorceiltrunc(self):
        from _numpypy import array, floor, ceil, trunc, complex128
        import math
        ninf, inf = float("-inf"), float("inf")
        a = array([ninf, -1.4, -1.5, -1.0, 0.0, 1.0, 1.4, 0.5, inf])
        assert ([ninf, -2.0, -2.0, -1.0, 0.0, 1.0, 1.0, 0.0, inf] == floor(a)).all()
        assert ([ninf, -1.0, -1.0, -1.0, 0.0, 1.0, 2.0, 1.0, inf] == ceil(a)).all()
        assert ([ninf, -1.0, -1.0, -1.0, 0.0, 1.0, 1.0, 0.0, inf] == trunc(a)).all()
        assert all([math.isnan(f(float("nan"))) for f in floor, ceil, trunc])
        assert all([math.copysign(1, f(abs(float("nan")))) == 1 for f in floor, ceil, trunc])
        assert all([math.copysign(1, f(-abs(float("nan")))) == -1 for f in floor, ceil, trunc])

        a = array([ complex(-1.4, -1.4), complex(-1.5, -1.5)]) 
        raises(TypeError, floor, a)
        raises(TypeError, ceil, a)
        raises(TypeError, trunc, a)

    def test_copysign(self):
        from _numpypy import array, copysign, complex128

        reference = [5.0, -0.0, 0.0, -6.0]
        a = array([-5.0, 0.0, 0.0, 6.0])
        b = array([5.0, -0.0, 3.0, -6.0])
        c = copysign(a, b)
        for i in range(4):
            assert c[i] == reference[i]

        b = array([True, True, True, True], dtype=bool)
        c = copysign(a, b)
        for i in range(4):
            assert c[i] == abs(a[i])

        a = complex128(complex(-5., 5.))
        b = complex128(complex(0., 0.))
        raises(TypeError, copysign, a, b)

    def test_exp(self):
        import math
        from _numpypy import array, exp

        a = array([-5.0, -0.0, 0.0, 12345678.0, float("inf"),
                   -float('inf'), -12343424.0])
        b = exp(a)
        for i in range(len(a)):
            try:
                res = math.exp(a[i])
            except OverflowError:
                res = float('inf')
            assert b[i] == res

    def test_exp2(self):
        import math 
        from _numpypy import array, exp2, complex128, complex64
        inf = float('inf')
        ninf = -float('inf')
        nan = float('nan')
        cmpl = complex

        a = array([-5.0, -0.0, 0.0, 2, 12345678.0, inf, ninf, -12343424.0])
        b = exp2(a)
        for i in range(len(a)):
            try:
                res = 2 ** a[i]
            except OverflowError:
                res = float('inf')
            assert b[i] == res

        assert exp2(3) == 8
        assert math.isnan(exp2(nan))

        for c,rel_err in ((complex128, 5e-323), (complex64, 1e-7)):
            a = [cmpl(-5., 0), cmpl(-5., -5.), cmpl(-5., 5.),
                       cmpl(0., -5.), cmpl(0., 0.), cmpl(0., 5.),
                       cmpl(-0., -5.), cmpl(-0., 0.), cmpl(-0., 5.),
                       cmpl(-0., -0.), cmpl(inf, 0.), cmpl(inf, 5.),
                       cmpl(inf, -0.), cmpl(ninf, 0.), cmpl(ninf, 5.),
                       cmpl(ninf, -0.), cmpl(ninf, inf), cmpl(inf, inf),
                       cmpl(ninf, ninf), cmpl(5., inf), cmpl(5., ninf),
                       cmpl(nan, 5.), cmpl(5., nan), cmpl(nan, nan),
                     ]
            b = exp2(array(a,dtype=c))
            for i in range(len(a)):
                try:
                    res = self.c_pow((2,0), (a[i].real, a[i].imag))
                    if a[i].imag == 0. and math.copysign(1., a[i].imag)<0:
                        res = (res[0], -0.)
                    elif a[i].imag == 0.:
                        res = (res[0], 0.)
                except OverflowError:
                    res = (inf, nan)
                except ValueError:
                    res = (nan, nan)
                msg = 'result of 2**%r(%r) got %r expected %r\n ' % \
                            (c,a[i], b[i], res)
                # cast untranslated boxed results to float,
                # does no harm when translated
                t1 = float(res[0])        
                t2 = float(b[i].real)        
                self.rAlmostEqual(t1, t2, rel_err=rel_err, msg=msg)
                t1 = float(res[1])        
                t2 = float(b[i].imag)        
                self.rAlmostEqual(t1, t2, rel_err=rel_err, msg=msg)

    def test_expm1(self):
        import math, cmath
        from _numpypy import array, expm1, complex128, complex64
        inf = float('inf')
        ninf = -float('inf')
        nan = float('nan')
        cmpl = complex

        a = array([-5.0, -0.0, 0.0, 12345678.0, float("inf"),
                   -float('inf'), -12343424.0])
        b = expm1(a)
        for i in range(4):
            try:
                res = math.exp(a[i]) - 1
            except OverflowError:
                res = float('inf')
            assert b[i] == res

        assert expm1(1e-50) == 1e-50

        for c,rel_err in ((complex128, 5e-323), (complex64, 1e-7)):
            a = [cmpl(-5., 0), cmpl(-5., -5.), cmpl(-5., 5.),
                       cmpl(0., -5.), cmpl(0., 0.), cmpl(0., 5.),
                       cmpl(-0., -5.), cmpl(-0., 0.), cmpl(-0., 5.),
                       cmpl(-0., -0.), cmpl(inf, 0.), cmpl(inf, 5.),
                       cmpl(inf, -0.), cmpl(ninf, 0.), cmpl(ninf, 5.),
                       cmpl(ninf, -0.), cmpl(ninf, inf), cmpl(inf, inf),
                       cmpl(ninf, ninf), cmpl(5., inf), cmpl(5., ninf),
                       cmpl(nan, 5.), cmpl(5., nan), cmpl(nan, nan),
                     ]
            b = expm1(array(a,dtype=c))
            got_err = False
            for i in range(len(a)):
                try:
                    res = cmath.exp(a[i]) - 1.
                    if a[i].imag == 0. and math.copysign(1., a[i].imag)<0:
                        res = cmpl(res.real, -0.)
                    elif a[i].imag == 0.:
                        res = cmpl(res.real, 0.)
                except OverflowError:
                    res = cmpl(inf, nan)
                except ValueError:
                    res = cmpl(nan, nan)
                msg = 'result of expm1(%r(%r)) got %r expected %r\n ' % \
                            (c,a[i], b[i], res)
                try:
                    # cast untranslated boxed results to float,
                    # does no harm when translated
                    t1 = float(res.real)        
                    t2 = float(b[i].real)        
                    self.rAlmostEqual(t1, t2, rel_err=rel_err, msg=msg)
                    t1 = float(res.imag)        
                    t2 = float(b[i].imag)        
                    self.rAlmostEqual(t1, t2, rel_err=rel_err, msg=msg)
                except AssertionError as e:
                    print e.message
                    got_err = True
        if got_err:
            raise AssertionError('Errors were printed to stdout')


    def test_sin(self):
        import math
        from _numpypy import array, sin

        a = array([0, 1, 2, 3, math.pi, math.pi*1.5, math.pi*2])
        b = sin(a)
        for i in range(len(a)):
            assert b[i] == math.sin(a[i])

        a = sin(array([True, False], dtype=bool))
        assert abs(a[0] - sin(1)) < 1e-3  # a[0] will be very imprecise
        assert a[1] == 0.0

    def test_cos(self):
        import math
        from _numpypy import array, cos

        a = array([0, 1, 2, 3, math.pi, math.pi*1.5, math.pi*2])
        b = cos(a)
        for i in range(len(a)):
            assert b[i] == math.cos(a[i])

    def test_tan(self):
        import math
        from _numpypy import array, tan

        a = array([0, 1, 2, 3, math.pi, math.pi*1.5, math.pi*2])
        b = tan(a)
        for i in range(len(a)):
            assert b[i] == math.tan(a[i])

    def test_arcsin(self):
        import math
        from _numpypy import array, arcsin

        a = array([-1, -0.5, -0.33, 0, 0.33, 0.5, 1])
        b = arcsin(a)
        for i in range(len(a)):
            assert b[i] == math.asin(a[i])

        a = array([-10, -1.5, -1.01, 1.01, 1.5, 10, float('nan'), float('inf'), float('-inf')])
        b = arcsin(a)
        for f in b:
            assert math.isnan(f)

    def test_arccos(self):
        import math
        from _numpypy import array, arccos

        a = array([-1, -0.5, -0.33, 0, 0.33, 0.5, 1])
        b = arccos(a)
        for i in range(len(a)):
            assert b[i] == math.acos(a[i])

        a = array([-10, -1.5, -1.01, 1.01, 1.5, 10, float('nan'), float('inf'), float('-inf')])
        b = arccos(a)
        for f in b:
            assert math.isnan(f)

    def test_arctan(self):
        import math
        from _numpypy import array, arctan

        a = array([-3, -2, -1, 0, 1, 2, 3, float('inf'), float('-inf')])
        b = arctan(a)
        for i in range(len(a)):
            assert b[i] == math.atan(a[i])

        a = array([float('nan')])
        b = arctan(a)
        assert math.isnan(b[0])

    def test_arctan2(self):
        import math
        from _numpypy import array, arctan2

        # From the numpy documentation
        assert (
            arctan2(
                [0.,  0.,           1.,          -1., float('inf'),  float('inf')],
                [0., -0., float('inf'), float('inf'), float('inf'), float('-inf')]) ==
            [0.,  math.pi,  0., -0.,  math.pi/4, 3*math.pi/4]).all()

        a = array([float('nan')])
        b = arctan2(a, 0)
        assert math.isnan(b[0])

    def test_sinh(self):
        import math
        from _numpypy import array, sinh

        a = array([-1, 0, 1, float('inf'), float('-inf')])
        b = sinh(a)
        for i in range(len(a)):
            assert b[i] == math.sinh(a[i])

    def test_cosh(self):
        import math
        from _numpypy import array, cosh

        a = array([-1, 0, 1, float('inf'), float('-inf')])
        b = cosh(a)
        for i in range(len(a)):
            assert b[i] == math.cosh(a[i])

    def test_tanh(self):
        import math
        from _numpypy import array, tanh

        a = array([-1, 0, 1, float('inf'), float('-inf')])
        b = tanh(a)
        for i in range(len(a)):
            assert b[i] == math.tanh(a[i])

    def test_arcsinh(self):
        import math
        from _numpypy import arcsinh

        for v in [float('inf'), float('-inf'), 1.0, math.e]:
            assert math.asinh(v) == arcsinh(v)
        assert math.isnan(arcsinh(float("nan")))

    def test_arccosh(self):
        import math
        from _numpypy import arccosh

        for v in [1.0, 1.1, 2]:
            assert math.acosh(v) == arccosh(v)
        for v in [-1.0, 0, .99]:
            assert math.isnan(arccosh(v))

    def test_arctanh(self):
        import math
        from _numpypy import arctanh

        for v in [.99, .5, 0, -.5, -.99]:
            assert math.atanh(v) == arctanh(v)
        for v in [2.0, -2.0]:
            assert math.isnan(arctanh(v))
        for v in [1.0, -1.0]:
            assert arctanh(v) == math.copysign(float("inf"), v)

    def test_sqrt(self):
        import math
        from _numpypy import sqrt

        nan, inf = float("nan"), float("inf")
        data = [1, 2, 3, inf]
        results = [math.sqrt(1), math.sqrt(2), math.sqrt(3), inf]
        assert (sqrt(data) == results).all()
        assert math.isnan(sqrt(-1))
        assert math.isnan(sqrt(nan))

    def test_square(self):
        import math
        from _numpypy import square

        nan, inf, ninf = float("nan"), float("inf"), float("-inf")

        assert math.isnan(square(nan))
        assert math.isinf(square(inf))
        assert math.isinf(square(ninf))
        assert square(ninf) > 0
        assert [square(x) for x in range(-5, 5)] == [x*x for x in range(-5, 5)]
        assert math.isinf(square(1e300))

    def test_radians(self):
        import math
        from _numpypy import radians, array
        a = array([
            -181, -180, -179,
            181, 180, 179,
            359, 360, 361,
            400, -1, 0, 1,
            float('inf'), float('-inf')])
        b = radians(a)
        for i in range(len(a)):
            assert b[i] == math.radians(a[i])

        raises(TypeError, radians, complex(90,90))

    def test_deg2rad(self):
        import math
        from _numpypy import deg2rad, array
        a = array([
            -181, -180, -179,
            181, 180, 179,
            359, 360, 361,
            400, -1, 0, 1,
            float('inf'), float('-inf')])
        b = deg2rad(a)
        for i in range(len(a)):
            assert b[i] == math.radians(a[i])

        raises(TypeError, deg2rad, complex(90,90))

    def test_degrees(self):
        import math
        from _numpypy import degrees, array
        a = array([
            -181, -180, -179,
            181, 180, 179,
            359, 360, 361,
            400, -1, 0, 1,
            float('inf'), float('-inf')])
        b = degrees(a)
        for i in range(len(a)):
            assert b[i] == math.degrees(a[i])

        raises(TypeError, degrees, complex(90,90))

    def test_rad2deg(self):
        import math
        from _numpypy import rad2deg, array
        a = array([
            -181, -180, -179,
            181, 180, 179,
            359, 360, 361,
            400, -1, 0, 1,
            float('inf'), float('-inf')])
        b = rad2deg(a)
        for i in range(len(a)):
            assert b[i] == math.degrees(a[i])

        raises(TypeError, rad2deg, complex(90,90))

    def test_reduce_errors(self):
        from _numpypy import sin, add

        raises(ValueError, sin.reduce, [1, 2, 3])
        assert add.reduce(1) == 1

    def test_reduce_1d(self):
        from _numpypy import add, maximum, less

        assert less.reduce([5, 4, 3, 2, 1])
        assert add.reduce([1, 2, 3]) == 6
        assert maximum.reduce([1]) == 1
        assert maximum.reduce([1, 2, 3]) == 3
        raises(ValueError, maximum.reduce, [])

    def test_reduceND(self):
        from _numpypy import add, arange
        a = arange(12).reshape(3, 4)
        assert (add.reduce(a, 0) == [12, 15, 18, 21]).all()
        assert (add.reduce(a, 1) == [6.0, 22.0, 38.0]).all()
        raises(ValueError, add.reduce, a, 2)

    def test_reduce_keepdims(self):
        from _numpypy import add, arange
        a = arange(12).reshape(3, 4)
        b = add.reduce(a, 0, keepdims=True)
        assert b.shape == (1, 4)
        assert (add.reduce(a, 0, keepdims=True) == [12, 15, 18, 21]).all()

    def test_bitwise(self):
        from _numpypy import bitwise_and, bitwise_or, bitwise_xor, arange, array
        a = arange(6).reshape(2, 3)
        assert (a & 1 == [[0, 1, 0], [1, 0, 1]]).all()
        assert (a & 1 == bitwise_and(a, 1)).all()
        assert (a | 1 == [[1, 1, 3], [3, 5, 5]]).all()
        assert (a | 1 == bitwise_or(a, 1)).all()
        assert (a ^ 3 == bitwise_xor(a, 3)).all()
        raises(TypeError, 'array([1.0]) & 1')

    def test_unary_bitops(self):
        from _numpypy import bitwise_not, invert, array
        a = array([1, 2, 3, 4])
        assert (~a == [-2, -3, -4, -5]).all()
        assert (bitwise_not(a) == ~a).all()
        assert (invert(a) == ~a).all()

    def test_shift(self):
        from _numpypy import left_shift, right_shift

        assert (left_shift([5, 1], [2, 13]) == [20, 2**13]).all()
        assert (right_shift(10, range(5)) == [10, 5, 2, 1, 0]).all()

    def test_comparisons(self):
        import operator
        from _numpypy import equal, not_equal, less, less_equal, greater, greater_equal

        for ufunc, func in [
            (equal, operator.eq),
            (not_equal, operator.ne),
            (less, operator.lt),
            (less_equal, operator.le),
            (greater, operator.gt),
            (greater_equal, operator.ge),
        ]:
            for a, b in [
                (3, 3),
                (3, 4),
                (4, 3),
                (3.0, 3.0),
                (3.0, 3.5),
                (3.5, 3.0),
                (3.0, 3),
                (3, 3.0),
                (3.5, 3),
                (3, 3.5),
            ]:
                assert ufunc(a, b) == func(a, b)


    def test_count_nonzero(self):
        from _numpypy import count_nonzero
        assert count_nonzero(0) == 0
        assert count_nonzero(1) == 1
        assert count_nonzero([]) == 0
        assert count_nonzero([1, 2, 0]) == 2
        assert count_nonzero([[1, 2, 0], [1, 0, 2]]) == 4

    def test_true_divide_2(self):
        from _numpypy import arange, array, true_divide
        assert (true_divide(arange(3), array([2, 2, 2])) == array([0, 0.5, 1])).all()

    def test_isnan_isinf(self):
        from _numpypy import isnan, isinf, float64, array
        assert isnan(float('nan'))
        assert isnan(float64(float('nan')))
        assert not isnan(3)
        assert isinf(float('inf'))
        assert not isnan(3.5)
        assert not isinf(3.5)
        assert not isnan(float('inf'))
        assert not isinf(float('nan'))
        assert (isnan(array([0.2, float('inf'), float('nan')])) == [False, False, True]).all()
        assert (isinf(array([0.2, float('inf'), float('nan')])) == [False, True, False]).all()
        assert isinf(array([0.2])).dtype.kind == 'b'

        assert (isnan(array([0.2+2j, complex(float('inf'),0), 
                complex(0,float('inf')), complex(0,float('nan')),
                complex(float('nan'), 0)], dtype=complex)) == \
                [False, False, False, True, True]).all()

        assert (isinf(array([0.2+2j, complex(float('inf'),0), 
                complex(0,float('inf')), complex(0,float('nan')),
                complex(float('nan'), 0)], dtype=complex)) == \
                [False, True, True, False, False]).all()

    def test_isposinf_isneginf(self):
        from _numpypy import isneginf, isposinf, complex128
        assert isposinf(float('inf'))
        assert not isposinf(float('-inf'))
        assert not isposinf(float('nan'))
        assert not isposinf(0)
        assert not isposinf(0.0)
        assert isneginf(float('-inf'))
        assert not isneginf(float('inf'))
        assert not isneginf(float('nan'))
        assert not isneginf(0)
        assert not isneginf(0.0)

        raises(TypeError, isneginf, complex(1, 1))
        raises(TypeError, isposinf, complex(1, 1))

    def test_isfinite(self):
        from _numpypy import isfinite
        inf = float('inf')
        ninf = -float('inf')
        nan = float('nan')
        assert (isfinite([0, 0.0, 1e50, -1e-50]) ==
            [True, True, True, True]).all()
        assert (isfinite([ninf, inf, -nan, nan]) ==
            [False, False, False, False]).all()

        a = [complex(0, 0), complex(1e50, -1e-50), complex(inf, 0),
             complex(inf, inf), complex(inf, ninf), complex(0, inf),
             complex(ninf, ninf), complex(nan, 0), complex(0, nan),
             complex(nan, nan)]
        assert (isfinite(a) == [True, True, False, False, False, 
                        False, False, False, False, False]).all() 

    def test_logical_ops(self):
        from _numpypy import logical_and, logical_or, logical_xor, logical_not

        assert (logical_and([True, False , True, True], [1, 1, 3, 0])
                == [True, False, True, False]).all()
        assert (logical_or([True, False, True, False], [1, 2, 0, 0])
                == [True, True, True, False]).all()
        assert (logical_xor([True, False, True, False], [1, 2, 0, 0])
                == [False, True, True, False]).all()
        assert (logical_not([True, False]) == [False, True]).all()

    def test_logn(self):
        import math
        from _numpypy import log, log2, log10

        for log_func, base in [(log, math.e), (log2, 2), (log10, 10)]:
            for v in [float('-nan'), float('-inf'), -1, float('nan')]:
                assert math.isnan(log_func(v))
            for v in [-0.0, 0.0]:
                assert log_func(v) == float("-inf")
            assert log_func(float('inf')) == float('inf')
            assert (log_func([1, base]) == [0, 1]).all()

    def test_log1p(self):
        import math
        from _numpypy import log1p

        for v in [float('-nan'), float('-inf'), -2, float('nan')]:
            assert math.isnan(log1p(v))
        for v in [-1]:
            assert log1p(v) == float("-inf")
        assert log1p(float('inf')) == float('inf')
        assert (log1p([0, 1e-50, math.e - 1]) == [0, 1e-50, 1]).all()

    def test_power_complex(self):
        import math, cmath
        inf = float('inf')
        ninf = -float('inf')
        nan = float('nan')
        cmpl = complex
        from _numpypy import power, array, complex128, complex64
        for c,rel_err in ((complex128, 5e-323), (complex64, 1e-7)):
            a = array([cmpl(-5., 0), cmpl(-5., -5.), cmpl(-5., 5.),
                       cmpl(0., -5.), cmpl(0., 0.), cmpl(0., 5.),
                       cmpl(-0., -5.), cmpl(-0., 0.), cmpl(-0., 5.),
                       cmpl(-0., -0.), cmpl(inf, 0.), cmpl(inf, 5.),
                       cmpl(inf, -0.), cmpl(ninf, 0.), cmpl(ninf, 5.),
                       cmpl(ninf, -0.), cmpl(ninf, inf), cmpl(inf, inf),
                       cmpl(ninf, ninf), cmpl(5., inf), cmpl(5., ninf),
                       cmpl(nan, 5.), cmpl(5., nan), cmpl(nan, nan),
                     ], dtype=c)
            got_err = False
            for p in (3, -1, 10000, 2.3, -10000, 10+3j):
                b = power(a, p)
                for i in range(len(a)):
                    r = a[i]**p
                    msg = 'result of %r(%r)**%r got %r expected %r\n ' % \
                            (c,a[i], p, b[i], r)
                    try:        
                        t1 = float(r.real)        
                        t2 = float(b[i].real)        
                        self.rAlmostEqual(t1, t2, rel_err=rel_err, msg=msg)
                        t1 = float(r.imag)        
                        t2 = float(b[i].imag)        
                        self.rAlmostEqual(t1, t2, rel_err=rel_err, msg=msg)
                    except AssertionError as e:
                        print e.message
                        got_err = True
            if got_err:
                raise AssertionError('Errors were printed to stdout')

    def test_power_float(self):
        import math
        from _numpypy import power, array
        a = array([1., 2., 3.])
        b = power(a, 3)
        for i in range(len(a)):
            assert b[i] == a[i] ** 3

        a = array([1., 2., 3.])
        b = array([1., 2., 3.])
        c = power(a, b)
        for i in range(len(a)):
            assert c[i] == a[i] ** b[i]

        assert power(2, float('inf')) == float('inf')
        assert power(float('inf'), float('inf')) == float('inf')
        assert power(12345.0, 12345.0) == float('inf')
        assert power(-12345.0, 12345.0) == float('-inf')
        assert power(-12345.0, 12346.0) == float('inf')
        assert math.isnan(power(-1, 1.1))
        assert math.isnan(power(-1, -1.1))
        assert power(-2.0, -1) == -0.5
        assert power(-2.0, -2) == 0.25
        assert power(12345.0, -12345.0) == 0
        assert power(float('-inf'), 2) == float('inf')
        assert power(float('-inf'), 2.5) == float('inf')
        assert power(float('-inf'), 3) == float('-inf')

    def test_power_int(self):
        import math
        from _numpypy import power, array
        a = array([1, 2, 3])
        b = power(a, 3)
        for i in range(len(a)):
            assert b[i] == a[i] ** 3

        a = array([1, 2, 3])
        b = array([1, 2, 3])
        c = power(a, b)
        for i in range(len(a)):
            assert c[i] == a[i] ** b[i]

        # assert power(12345, 12345) == -9223372036854775808
        # assert power(-12345, 12345) == -9223372036854775808
        # assert power(-12345, 12346) == -9223372036854775808
        assert power(2, 0) == 1
        assert power(2, -1) == 0
        assert power(2, -2) == 0
        assert power(-2, -1) == 0
        assert power(-2, -2) == 0
        assert power(12345, -12345) == 0

    def test_floordiv(self):
        from _numpypy import floor_divide, array
        import math
        a = array([1., 2., 3., 4., 5., 6., 6.01])
        b = floor_divide(a, 2.5)
        for i in range(len(a)):
            assert b[i] == a[i] // 2.5
        
        a = array([10+10j, -15-100j, 0+10j], dtype=complex)
        b = floor_divide(a, 2.5)
        for i in range(len(a)):
            assert b[i] == a[i] // 2.5
        b = floor_divide(a, 2.5+3j)
        #numpy returns (a.real*b.real + a.imag*b.imag) / abs(b)**2
        expect = [3., -23., 1.]
        for i in range(len(a)):
            assert b[i] == expect[i] 
        b = floor_divide(a[0], 0.)
        assert math.isnan(b.real)
        assert b.imag == 0.

    def test_logaddexp(self):
        import math
        import sys
        float_max, float_min = sys.float_info.max, sys.float_info.min
        from _numpypy import logaddexp

        # From the numpy documentation
        prob1 = math.log(1e-50)
        prob2 = math.log(2.5e-50)
        prob12 = logaddexp(prob1, prob2)
        assert math.fabs(-113.87649168120691 - prob12) < 0.000000000001

        assert logaddexp(0, 0) == math.log(2)
        assert logaddexp(float('-inf'), 0) == 0
        assert logaddexp(float_max, float_max) == float_max
        assert logaddexp(float_min, float_min) == math.log(2)

        assert math.isnan(logaddexp(float('nan'), 1))
        assert math.isnan(logaddexp(1, float('nan')))
        assert math.isnan(logaddexp(float('nan'), float('inf')))
        assert math.isnan(logaddexp(float('inf'), float('nan')))
        assert logaddexp(float('-inf'), float('-inf')) == float('-inf')
        assert logaddexp(float('-inf'), float('inf')) == float('inf')
        assert logaddexp(float('inf'), float('-inf')) == float('inf')
        assert logaddexp(float('inf'), float('inf')) == float('inf')

    def test_logaddexp2(self):
        import math
        import sys
        float_max, float_min = sys.float_info.max, sys.float_info.min
        from _numpypy import logaddexp2
        log2 = math.log(2)

        # From the numpy documentation
        prob1 = math.log(1e-50) / log2
        prob2 = math.log(2.5e-50) / log2
        prob12 = logaddexp2(prob1, prob2)
        assert math.fabs(-164.28904982231052 - prob12) < 0.000000000001

        assert logaddexp2(0, 0) == 1
        assert logaddexp2(float('-inf'), 0) == 0
        assert logaddexp2(float_max, float_max) == float_max
        assert logaddexp2(float_min, float_min) == 1.0

        assert math.isnan(logaddexp2(float('nan'), 1))
        assert math.isnan(logaddexp2(1, float('nan')))
        assert math.isnan(logaddexp2(float('nan'), float('inf')))
        assert math.isnan(logaddexp2(float('inf'), float('nan')))
        assert logaddexp2(float('-inf'), float('-inf')) == float('-inf')
        assert logaddexp2(float('-inf'), float('inf')) == float('inf')
        assert logaddexp2(float('inf'), float('-inf')) == float('inf')
        assert logaddexp2(float('inf'), float('inf')) == float('inf')

    def test_conjugate(self):
        from _numpypy import conj, conjugate, complex128, complex64
        import _numpypy as np

        c0 = complex128(complex(2.5, 0))
        c1 = complex64(complex(1, 2))

        assert conj is conjugate
        assert conj(c0) == c0
        assert conj(c1) == complex(1, -2)
        assert conj(1) == 1
        assert conj(-3) == -3
        assert conj(float('-inf')) == float('-inf')


        assert np.conjugate(1+2j) == 1-2j

        x = np.eye(2) + 1j * np.eye(2)
        for a, b in zip(np.conjugate(x), np.array([[ 1.-1.j,  0.-0.j], [ 0.-0.j,  1.-1.j]])):
            assert a[0] == b[0]
            assert a[1] == b[1]


    def test_complex(self):
        from _numpypy import (complex128, complex64, add,
            subtract as sub, multiply, divide, negative, abs, fmod, 
            reciprocal)
        from _numpypy import (equal, not_equal, greater, greater_equal, less,
                less_equal)

        for complex_ in complex64, complex128:

            O = complex(0, 0)
            c0 = complex_(complex(2.5, 0))
            c1 = complex_(complex(1, 2))
            c2 = complex_(complex(3, 4))
            c3 = complex_(complex(-3, -3))

            assert equal(c0, 2.5)
            assert equal(c1, complex_(complex(1, 2)))
            assert equal(c1, complex(1, 2))
            assert equal(c1, c1)
            assert not_equal(c1, c2)
            assert not equal(c1, c2)

            assert less(c1, c2)
            assert less_equal(c1, c2)
            assert less_equal(c1, c1)
            assert not less(c1, c1)

            assert greater(c2, c1)
            assert greater_equal(c2, c1)
            assert not greater(c1, c2)

            assert add(c1, c2) == complex_(complex(4, 6))
            assert add(c1, c2) == complex(4, 6)
            
            assert sub(c0, c0) == sub(c1, c1) == 0
            assert sub(c1, c2) == complex(-2, -2)
            assert negative(complex(1,1)) == complex(-1, -1)
            assert negative(complex(0, 0)) == 0
            

            assert multiply(1, c1) == c1
            assert multiply(2, c2) == complex(6, 8)
            assert multiply(c1, c2) == complex(-5, 10)

            assert divide(c0, 1) == c0
            assert divide(c2, -1) == negative(c2)
            assert divide(c1, complex(0, 1)) == complex(2, -1)
            n = divide(c1, O)
            assert repr(n.real) == 'inf'
            assert repr(n.imag).startswith('inf') #can be inf*j or infj
            assert divide(c0, c0) == 1
            res = divide(c2, c1)
            assert abs(res.real-2.2) < 0.001
            assert abs(res.imag+0.4) < 0.001

            assert abs(c0) == 2.5
            assert abs(c2) == 5
            
            raises (TypeError, fmod, c0, 3) 
            inf_c = complex_(complex(float('inf'), 0.))
            assert repr(abs(inf_c)) == 'inf'
            assert repr(abs(complex(float('nan'), float('nan')))) == 'nan'

        assert False, 'untested: ' + \
                     'numpy.real. numpy.imag' + \
                     'expm1, ' + \
                     'log2, log1p, ' + \
                     'logaddexp, npy_log2_1p, logaddexp2'

    def test_complex_math(self):
        if self.isWindows:
            skip('windows does not support c99 complex')
        import  _numpypy as np
        rAlmostEqual = self.rAlmostEqual

        def parse_testfile(fname):
            """Parse a file with test values

            Empty lines or lines starting with -- are ignored
            yields id, fn, arg_real, arg_imag, exp_real, exp_imag
            """
            with open(fname) as fp:
                for line in fp:
                    # skip comment lines and blank lines
                    if line.startswith('--') or not line.strip():
                        continue

                    lhs, rhs = line.split('->')
                    id, fn, arg_real, arg_imag = lhs.split()
                    rhs_pieces = rhs.split()
                    exp_real, exp_imag = rhs_pieces[0], rhs_pieces[1]
                    flags = rhs_pieces[2:]

                    yield (id, fn,
                           float(arg_real), float(arg_imag),
                           float(exp_real), float(exp_imag),
                           flags
                          )
        for complex_, abs_err, testcases in (\
                 (np.complex128, 5e-323, self.testcases128),
                 (np.complex64,  5e-32,  self.testcases64), 
                ):
            for id, fn, ar, ai, er, ei, flags in parse_testfile(testcases):
                arg = complex_(complex(ar, ai))
                expected = (er, ei)
                if fn.startswith('acos'):
                    fn = 'arc' + fn[1:]
                elif fn.startswith('asin'):
                    fn = 'arc' + fn[1:]
                elif fn.startswith('atan'):
                    fn = 'arc' + fn[1:]
                elif fn in ('rect', 'polar'):
                    continue
                function = getattr(np, fn)
                _actual = function(arg)
                actual = (_actual.real, _actual.imag)

                if 'ignore-real-sign' in flags:
                    actual = (abs(actual[0]), actual[1])
                    expected = (abs(expected[0]), expected[1])
                if 'ignore-imag-sign' in flags:
                    actual = (actual[0], abs(actual[1]))
                    expected = (expected[0], abs(expected[1]))

                # for the real part of the log function, we allow an
                # absolute error of up to 2e-15.
                if fn in ('log', 'log10'):
                    real_abs_err = 2e-15
                else:
                    real_abs_err = abs_err

                error_message = (
                    '%s: %s(%r(%r, %r))\n'
                    'Expected: complex(%r, %r)\n'
                    'Received: complex(%r, %r)\n'
                    ) % (id, fn, complex_, ar, ai,
                         expected[0], expected[1],
                         actual[0], actual[1])
    
                # since rAlmostEqual is a wrapped function,
                # convert arguments to avoid boxed values
                rAlmostEqual(float(expected[0]), float(actual[0]),
                               abs_err=real_abs_err, msg=error_message)
                rAlmostEqual(float(expected[1]), float(actual[1]),
                                   msg=error_message)
