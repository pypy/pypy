# spaceconfig = {"usemodules" : ["binascii", "time", "struct"]}
from random import random
import cmath

def close_abs(x, y, eps=1e-9):
    """Return true iff floats x and y "are close\""""
    # put the one with larger magnitude second
    if abs(x) > abs(y):
        x, y = y, x
    if y == 0:
        return abs(x) < eps
    if x == 0:
        return abs(y) < eps
    # check that relative difference < eps
    return abs((x - y) / y) < eps

def almost_equal(a, b, eps=1e-9):
    if isinstance(a, complex):
        if isinstance(b, complex):
            return a.real - b.real < eps and a.imag - b.imag < eps
        else:
            return a.real - b < eps and a.imag < eps
    else:
        if isinstance(b, complex):
            return a - b.real < eps and b.imag < eps
        else:
            return a - b < eps

def close(x, y):
    """Return true iff complexes x and y "are close\""""
    return close_abs(x.real, y.real) and close_abs(x.imag, y.imag)

def check_div(x, y):
    """Compute complex z=x*y, and check that z/x==y and z/y==x."""
    z = x * y
    if x != 0:
        q = z / x
        assert close(q, y)
        q = z.__div__(x)
        assert close(q, y)
        q = z.__truediv__(x)
        assert close(q, y)
    if y != 0:
        q = z / y
        assert close(q, x)
        q = z.__div__(y)
        assert close(q, x)
        q = z.__truediv__(y)
        assert close(q, x)

def test_div():
    # XXX this test passed but took waaaaay to long
    # look at dist/lib-python/modified-2.5.2/test/test_complex.py
    #simple_real = [float(i) for i in xrange(-5, 6)]
    simple_real = [-2.0, 0.0, 1.0]
    simple_complex = [complex(x, y) for x in simple_real for y in simple_real]
    for x in simple_complex:
        for y in simple_complex:
            check_div(x, y)

    # A naive complex division algorithm (such as in 2.0) is very prone to
    # nonsense errors for these (overflows and underflows).
    check_div(complex(1e200, 1e200), 1+0j)
    check_div(complex(1e-200, 1e-200), 1+0j)

    # Just for fun.
    for i in xrange(100):
        check_div(complex(random(), random()),
                       complex(random(), random()))

    raises(ZeroDivisionError, complex.__div__, 1+1j, 0+0j)
    # FIXME: The following currently crashes on Alpha
    raises(OverflowError, pow, 1e200+1j, 1e200+1j)

def test_truediv():
    assert almost_equal(complex.__truediv__(2+0j, 1+1j), 1-1j)
    raises(ZeroDivisionError, complex.__truediv__, 1+1j, 0+0j)

def test_floordiv():
    assert almost_equal(complex.__floordiv__(3+0j, 1.5+0j), 2)
    raises(ZeroDivisionError, complex.__floordiv__, 3+0j, 0+0j)

def test_coerce():
    raises(OverflowError, complex.__coerce__, 1+1j, 1L<<10000)

def test_convert():
    exc = raises(TypeError, complex.__int__, 3j)
    assert str(exc.value) == "can't convert complex to int"
    exc = raises(TypeError, complex.__float__, 3j)
    assert str(exc.value) == "can't convert complex to float"

def test_richcompare():
    assert complex.__lt__(1+1j, None) is NotImplemented
    assert complex.__eq__(1+1j, 2+2j) is False
    assert complex.__eq__(1+1j, 1+1j) is True
    assert complex.__ne__(1+1j, 1+1j) is False
    assert complex.__ne__(1+1j, 2+2j) is True
    raises(TypeError, complex.__lt__, 1+1j, 2+2j)
    raises(TypeError, complex.__le__, 1+1j, 2+2j)
    raises(TypeError, complex.__gt__, 1+1j, 2+2j)
    raises(TypeError, complex.__ge__, 1+1j, 2+2j)
    large = 1 << 10000
    assert not (5+0j) == large
    assert not large == (5+0j)
    assert (5+0j) != large
    assert large != (5+0j)

def test_richcompare_numbers():
    for n in 8, 8L, 0.01:
        assert complex.__eq__(n+0j, n)
        assert not complex.__ne__(n+0j, n)
        assert not complex.__eq__(complex(n, n), n)
        assert complex.__ne__(complex(n, n), n)
        raises(TypeError, complex.__lt__, n+0j, n)

def test_richcompare_boundaries():
    z = 9007199254740992+0j
    i = 9007199254740993
    assert not complex.__eq__(z, i)
    assert not complex.__eq__(z, long(i))
    assert complex.__ne__(z, i)
    assert complex.__ne__(z, long(i))

def test_mod():
    raises(ZeroDivisionError, (1+1j).__mod__, 0+0j)

    a = 3.33+4.43j
    raises(ZeroDivisionError, "a % 0")

def test_divmod():
    raises(ZeroDivisionError, divmod, 1+1j, 0+0j)

def test_pow():
    assert almost_equal(pow(1+1j, 0+0j), 1.0)
    assert almost_equal(pow(0+0j, 2+0j), 0.0)
    raises(ZeroDivisionError, pow, 0+0j, 1j)
    assert almost_equal(pow(1j, -1), 1/1j)
    assert almost_equal(pow(1j, 200), 1)
    raises(ValueError, pow, 1+1j, 1+1j, 1+1j)

    a = 3.33+4.43j
    assert a ** 0j == 1
    assert a ** 0.+0.j == 1

    assert 3j ** 0j == 1
    assert 3j ** 0 == 1

    raises(ZeroDivisionError, "0j ** a")
    raises(ZeroDivisionError, "0j ** (3-2j)")

    # The following is used to exercise certain code paths
    assert a ** 105 == a ** 105
    assert a ** -105 == a ** -105
    assert a ** -30 == a ** -30
    assert a ** 2 == a * a

    assert 0.0j ** 0 == 1

    b = 5.1+2.3j
    raises(ValueError, pow, a, b, 0)

    b = complex(float('inf'), 0.0) ** complex(10., 3.)
    assert repr(b) == "(nan+nanj)"

def test_boolcontext():
    for i in xrange(100):
        assert complex(random() + 1e-6, random() + 1e-6)
    assert not complex(0.0, 0.0)

def test_conjugate():
    assert close(complex(5.3, 9.8).conjugate(), 5.3-9.8j)

def test_constructor():
    class OS:
        def __init__(self, value):
            self.value = value
        def __complex__(self):
            return self.value
    class NS(object):
        def __init__(self, value):
            self.value = value
        def __complex__(self):
            return self.value
    assert complex(OS(1+10j)) == 1+10j
    assert complex(NS(1+10j)) == 1+10j
    assert complex(OS(1+10j), 5) == 1+15j
    assert complex(NS(1+10j), 5) == 1+15j
    assert complex(OS(1+10j), 5j) == -4+10j
    assert complex(NS(1+10j), 5j) == -4+10j

    raises(TypeError, complex, OS(None))
    raises(TypeError, complex, NS(None))

    # -- The following cases are not supported by CPython, but they
    # -- are supported by PyPy, which is most probably ok
    #raises((TypeError, AttributeError), complex, OS(1+10j), OS(1+10j))
    #raises((TypeError, AttributeError), complex, NS(1+10j), OS(1+10j))
    #raises((TypeError, AttributeError), complex, OS(1+10j), NS(1+10j))
    #raises((TypeError, AttributeError), complex, NS(1+10j), NS(1+10j))

    class F(object):
        def __float__(self):
            return 2.0
    assert complex(OS(1+10j), F()) == 1+12j
    assert complex(NS(1+10j), F()) == 1+12j

    assert almost_equal(complex("1+10j"), 1+10j)
    assert almost_equal(complex(10), 10+0j)
    assert almost_equal(complex(10.0), 10+0j)
    assert almost_equal(complex(10L), 10+0j)
    assert almost_equal(complex(10+0j), 10+0j)
    assert almost_equal(complex(1,10), 1+10j)
    assert almost_equal(complex(1,10L), 1+10j)
    assert almost_equal(complex(1,10.0), 1+10j)
    assert almost_equal(complex(1L,10), 1+10j)
    assert almost_equal(complex(1L,10L), 1+10j)
    assert almost_equal(complex(1L,10.0), 1+10j)
    assert almost_equal(complex(1.0,10), 1+10j)
    assert almost_equal(complex(1.0,10L), 1+10j)
    assert almost_equal(complex(1.0,10.0), 1+10j)
    assert almost_equal(complex(3.14+0j), 3.14+0j)
    assert almost_equal(complex(3.14), 3.14+0j)
    assert almost_equal(complex(314), 314.0+0j)
    assert almost_equal(complex(314L), 314.0+0j)
    assert almost_equal(complex(3.14+0j, 0j), 3.14+0j)
    assert almost_equal(complex(3.14, 0.0), 3.14+0j)
    assert almost_equal(complex(314, 0), 314.0+0j)
    assert almost_equal(complex(314L, 0L), 314.0+0j)
    assert almost_equal(complex(0j, 3.14j), -3.14+0j)
    assert almost_equal(complex(0.0, 3.14j), -3.14+0j)
    assert almost_equal(complex(0j, 3.14), 3.14j)
    assert almost_equal(complex(0.0, 3.14), 3.14j)
    assert almost_equal(complex("1"), 1+0j)
    assert almost_equal(complex("1j"), 1j)
    assert almost_equal(complex(),  0)
    assert almost_equal(complex("-1"), -1)
    assert almost_equal(complex("+1"), +1)
    assert almost_equal(complex(" ( +3.14-6J ) "), 3.14-6j)
    exc = raises(ValueError, complex, " ( +3.14- 6J ) ")
    assert str(exc.value) == "complex() arg is a malformed string"

    class complex2(complex):
        pass
    assert almost_equal(complex(complex2(1+1j)), 1+1j)
    assert almost_equal(complex(real=17, imag=23), 17+23j)
    assert almost_equal(complex(real=17+23j), 17+23j)
    assert almost_equal(complex(real=17+23j, imag=23), 17+46j)
    assert almost_equal(complex(real=1+2j, imag=3+4j), -3+5j)

    c = 3.14 + 1j
    assert complex(c) is c
    del c

    raises(TypeError, complex, "1", "1")
    raises(TypeError, complex, 1, "1")

    assert complex("  3.14+J  ") == 3.14+1j
    #h.assertEqual(complex(unicode("  3.14+J  ")), 3.14+1j)

    # SF bug 543840:  complex(string) accepts strings with \0
    # Fixed in 2.3.
    raises(ValueError, complex, '1+1j\0j')

    raises(TypeError, int, 5+3j)
    raises(TypeError, long, 5+3j)
    raises(TypeError, float, 5+3j)
    raises(ValueError, complex, "")
    raises(TypeError, complex, None)
    raises(ValueError, complex, "\0")
    raises(TypeError, complex, "1", "2")
    raises(TypeError, complex, "1", 42)
    raises(TypeError, complex, 1, "2")
    raises(ValueError, complex, "1+")
    raises(ValueError, complex, "1+1j+1j")
    raises(ValueError, complex, "--")
#        if x_test_support.have_unicode:
#            raises(ValueError, complex, unicode("1"*500))
#            raises(ValueError, complex, unicode("x"))
#
    class EvilExc(Exception):
        pass

    class evilcomplex:
        def __complex__(self):
            raise EvilExc

    raises(EvilExc, complex, evilcomplex())

    class float2:
        def __init__(self, value):
            self.value = value
        def __float__(self):
            return self.value

    assert almost_equal(complex(float2(42.)), 42)
    assert almost_equal(complex(real=float2(17.), imag=float2(23.)), 17+23j)
    raises(TypeError, complex, float2(None))


def test_constructor_bad_error_message():
    err = raises(TypeError, complex, {}).value
    assert "float" not in str(err)
    assert str(err) == "complex() first argument must be a string or a number, not 'dict'"
    err = raises(TypeError, complex, 1, {}).value
    assert "float" not in str(err)
    assert str(err) == "complex() second argument must be a number, not 'dict'"

def test_error_messages():
    err = raises(ZeroDivisionError, "1+1j / 0").value
    assert str(err) == "complex division by zero"
    err = raises(ZeroDivisionError, "1+1j // 0").value
    assert str(err) == "complex division by zero"

def test___complex___returning_non_complex():

    class Obj(object):
        def __init__(self, value):
            self.value = value
        def __complex__(self):
            return self.value

    # "bug-to-bug" compatibility to CPython: complex() is more relaxed in
    # what __complex__ can return. cmath functions really wants a complex
    # number to be returned by __complex__.
    assert complex(Obj(2.0)) == 2+0j
    assert complex(Obj(2)) == 2+0j
    assert complex(Obj(2L)) == 2+0j
    #
    assert cmath.polar(1) == (1.0, 0.0)
    raises(TypeError, "cmath.polar(Obj(1))")

def test_hash():
    for x in xrange(-30, 30):
        assert hash(x) == hash(complex(x, 0))
        x /= 3.0    # now check against floating point
        assert hash(x) == hash(complex(x, 0.))

def test_abs():
    nums = [complex(x/3., y/7.) for x in xrange(-9,9) for y in xrange(-9,9)]
    for num in nums:
        assert almost_equal((num.real**2 + num.imag**2)  ** 0.5, abs(num))

def test_complex_subclass_ctr():
    import sys
    class j(complex):
        pass
    assert j(100 + 0j) == 100 + 0j
    assert isinstance(j(100), j)
    assert j(100L + 0j) == 100 + 0j
    assert j("100+0j") == 100 + 0j
    exc = raises(ValueError, j, "100 + 0j")
    assert str(exc.value) == "complex() arg is a malformed string"
    x = j(1+0j)
    x.foo = 42
    assert x.foo == 42
    assert type(complex(x)) == complex

def test_infinity():
    inf = 1e200*1e200
    assert complex("1"*500) == complex(inf)
    assert complex("-inf") == complex(-inf)

def test_repr():
    assert repr(1+6j) == '(1+6j)'
    assert repr(1-6j) == '(1-6j)'

    assert repr(-(1+0j)) == '(-1-0j)'
    assert repr(complex( 0.0,  0.0)) == '0j'
    assert repr(complex( 0.0, -0.0)) == '-0j'
    assert repr(complex(-0.0,  0.0)) == '(-0+0j)'
    assert repr(complex(-0.0, -0.0)) == '(-0-0j)'
    assert repr(complex(1e45)) == "(" + repr(1e45) + "+0j)"
    assert repr(complex(1e200*1e200)) == '(inf+0j)'
    assert repr(complex(1,-float("nan"))) == '(1+nanj)'

def test_neg():
    assert -(1+6j) == -1-6j

def test_file():
    import os
    import tempfile

    a = 3.33+4.43j
    b = 5.1+2.3j

    fo = None
    try:
        pth = tempfile.mktemp()
        fo = open(pth,"wb")
        print >>fo, a, b
        fo.close()
        fo = open(pth, "rb")
        res = fo.read()
        assert res == "%s %s\n" % (a, b)
    finally:
        if (fo is not None) and (not fo.closed):
            fo.close()
        try:
            os.remove(pth)
        except (OSError, IOError):
            pass

def test_convert():
    raises(TypeError, int, 1+1j)
    raises(TypeError, float, 1+1j)

    class complex0(complex):
        """Test usage of __complex__() when inheriting from 'complex'"""
        def __complex__(self):
            return 42j
    assert complex(complex0(1j)) ==  42j

    class complex1(complex):
        """Test usage of __complex__() with a __new__() method"""
        def __new__(self, value=0j):
            return complex.__new__(self, 2*value)
        def __complex__(self):
            return self
    assert complex(complex1(1j)) == 2j

    class complex2(complex):
        """Make sure that __complex__() calls fail if anything other than a
        complex is returned"""
        def __complex__(self):
            return None
    raises(TypeError, complex, complex2(1j))

def test_getnewargs():
    assert (1+2j).__getnewargs__() == (1.0, 2.0)

def test_method_not_found_on_newstyle_instance():
    class A(object):
        pass
    a = A()
    a.__complex__ = lambda: 5j     # ignored
    raises(TypeError, complex, a)
    A.__complex__ = lambda self: 42j
    assert complex(a) == 42j

def test_format():
    # empty format string is same as str()
    assert format(1+3j, '') == str(1+3j)
    assert format(1.5+3.5j, '') == str(1.5+3.5j)
    assert format(3j, '') == str(3j)
    assert format(3.2j, '') == str(3.2j)
    assert format(3+0j, '') == str(3+0j)
    assert format(3.2+0j, '') == str(3.2+0j)

    # empty presentation type should still be analogous to str,
    # even when format string is nonempty (issue #5920).

    assert format(3.2, '-') == str(3.2)
    assert format(3.2+0j, '-') == str(3.2+0j)
    assert format(3.2+0j, '<') == str(3.2+0j)
    z = 10/7. - 100j/7.
    assert format(z, '') == str(z)
    assert format(z, '-') == str(z)
    assert format(z, '<') == str(z)
    assert format(z, '10') == str(z)
    z = complex(0.0, 3.0)
    assert format(z, '') == str(z)
    assert format(z, '-') == str(z)
    assert format(z, '<') == str(z)
    assert format(z, '2') == str(z)
    z = complex(-0.0, 2.0)
    assert format(z, '') == str(z)
    assert format(z, '-') == str(z)
    assert format(z, '<') == str(z)
    assert format(z, '3') == str(z)

    assert format(1+3j, 'g') == '1+3j'
    assert format(3j, 'g') == '0+3j'
    assert format(1.5+3.5j, 'g') == '1.5+3.5j'

    assert format(1.5+3.5j, '+g') == '+1.5+3.5j'
    assert format(1.5-3.5j, '+g') == '+1.5-3.5j'
    assert format(1.5-3.5j, '-g') == '1.5-3.5j'
    assert format(1.5+3.5j, ' g') == ' 1.5+3.5j'
    assert format(1.5-3.5j, ' g') == ' 1.5-3.5j'
    assert format(-1.5+3.5j, ' g') == '-1.5+3.5j'
    assert format(-1.5-3.5j, ' g') == '-1.5-3.5j'

    assert format(-1.5-3.5e-20j, 'g') == '-1.5-3.5e-20j'
    assert format(-1.5-3.5j, 'f') == '-1.500000-3.500000j'
    assert format(-1.5-3.5j, 'F') == '-1.500000-3.500000j'
    assert format(-1.5-3.5j, 'e') == '-1.500000e+00-3.500000e+00j'
    assert format(-1.5-3.5j, '.2e') == '-1.50e+00-3.50e+00j'
    assert format(-1.5-3.5j, '.2E') == '-1.50E+00-3.50E+00j'
    assert format(-1.5e10-3.5e5j, '.2G') == '-1.5E+10-3.5E+05j'

    assert format(1.5+3j, '<20g') ==  '1.5+3j              '
    assert format(1.5+3j, '*<20g') == '1.5+3j**************'
    assert format(1.5+3j, '>20g') ==  '              1.5+3j'
    assert format(1.5+3j, '^20g') ==  '       1.5+3j       '
    assert format(1.5+3j, '<20') ==   '(1.5+3j)            '
    assert format(1.5+3j, '>20') ==   '            (1.5+3j)'
    assert format(1.5+3j, '^20') ==   '      (1.5+3j)      '
    assert format(1.123-3.123j, '^20.2') == '     (1.1-3.1j)     '

    assert format(1.5+3j, '20.2f') == '          1.50+3.00j'
    assert format(1.5+3j, '>20.2f') == '          1.50+3.00j'
    assert format(1.5+3j, '<20.2f') == '1.50+3.00j          '
    assert format(1.5e20+3j, '<20.2f') == '150000000000000000000.00+3.00j'
    assert format(1.5e20+3j, '>40.2f') == '          150000000000000000000.00+3.00j'
    assert format(1.5e20+3j, '^40,.2f') == '  150,000,000,000,000,000,000.00+3.00j  '
    assert format(1.5e21+3j, '^40,.2f') == ' 1,500,000,000,000,000,000,000.00+3.00j '
    assert format(1.5e21+3000j, ',.2f') == '1,500,000,000,000,000,000,000.00+3,000.00j'

    # alternate is invalid
    raises(ValueError, (1.5+0.5j).__format__, '#f')

    # zero padding is invalid
    raises(ValueError, (1.5+0.5j).__format__, '010f')

    # '=' alignment is invalid
    raises(ValueError, (1.5+3j).__format__, '=20')

    # integer presentation types are an error
    for t in 'bcdoxX%':
        raises(ValueError, (1.5+0.5j).__format__, t)

    # make sure everything works in ''.format()
    assert '*{0:.3f}*'.format(3.14159+2.71828j) == '*3.142+2.718j*'
    assert u'*{0:.3f}*'.format(3.14159+2.71828j) == u'*3.142+2.718j*'
    assert u'{:-}'.format(1.5+3.5j) == u'(1.5+3.5j)'

    INF = float("inf")
    NAN = float("nan")
    # issue 3382: 'f' and 'F' with inf's and nan's
    assert '{0:f}'.format(INF+0j) == 'inf+0.000000j'
    assert '{0:F}'.format(INF+0j) == 'INF+0.000000j'
    assert '{0:f}'.format(-INF+0j) == '-inf+0.000000j'
    assert '{0:F}'.format(-INF+0j) == '-INF+0.000000j'
    assert '{0:f}'.format(complex(INF, INF)) == 'inf+infj'
    assert '{0:F}'.format(complex(INF, INF)) == 'INF+INFj'
    assert '{0:f}'.format(complex(INF, -INF)) == 'inf-infj'
    assert '{0:F}'.format(complex(INF, -INF)) == 'INF-INFj'
    assert '{0:f}'.format(complex(-INF, INF)) == '-inf+infj'
    assert '{0:F}'.format(complex(-INF, INF)) == '-INF+INFj'
    assert '{0:f}'.format(complex(-INF, -INF)) == '-inf-infj'
    assert '{0:F}'.format(complex(-INF, -INF)) == '-INF-INFj'

    assert '{0:f}'.format(complex(NAN, 0)) == 'nan+0.000000j'
    assert '{0:F}'.format(complex(NAN, 0)) == 'NAN+0.000000j'
    assert '{0:f}'.format(complex(NAN, NAN)) == 'nan+nanj'
    assert '{0:F}'.format(complex(NAN, NAN)) == 'NAN+NANj'

def test_complex_two_arguments():
    raises(TypeError, complex, 5, None)

def test_hash_minus_one():
    assert hash(-1.0 + 0j) == -2
    assert (-1.0 + 0j).__hash__() == -2

def test_int_override():
    class MyComplex(complex):
        def __int__(self):
            return 42

    c = MyComplex(0.j)
    assert int(c) == 42
