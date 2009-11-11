import py
from pypy.objspace.std import complexobject as cobj
from pypy.objspace.std import complextype as cobjtype
from pypy.objspace.std.objspace import FailedToImplement
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std import StdObjSpace

EPS = 1e-9

class TestW_ComplexObject:

    def _test_instantiation(self):
        def _t_complex(r=0.0,i=0.0):
            c = cobj.W_ComplexObject(r, i)
            assert c.real == float(r) and c.imag == float(i)
        pairs = (
            (1, 1),
            (1.0, 2.0),
            (2L, 3L),
        )
        for r,i in pairs:
            _t_complex(r,i)

    def test_parse_complex(self):
        f = cobjtype._split_complex
        def test_cparse(cnum, realnum, imagnum):
            result = f(cnum)
            assert len(result) == 2
            r, i = result
            assert r == realnum
            assert i == imagnum

        test_cparse('3', '3', '0.0')
        test_cparse('3+3j', '3', '3')
        test_cparse('3.0+3j', '3.0', '3')
        test_cparse('3L+3j', '3L', '3')
        test_cparse('3j', '0.0', '3')
        test_cparse('.e+5', '.e+5', '0.0')

    def test_pow(self):
        assert cobj._pow((0.0,2.0),(0.0,0.0)) == (1.0,0.0)
        assert cobj._pow((0.0,0.0),(2.0,0.0)) == (0.0,0.0)
        rr, ir = cobj._pow((0.0,1.0),(2.0,0.0))
        assert abs(-1.0 - rr) < EPS
        assert abs(0.0 - ir) < EPS

        assert cobj._powu((0.0,2.0),0) == (1.0,0.0)
        assert cobj._powu((0.0,0.0),2) == (0.0,0.0)
        assert cobj._powu((0.0,1.0),2) == (-1.0,0.0)
        assert cobj._powi((0.0,2.0),0) == (1.0,0.0)
        assert cobj._powi((0.0,0.0),2) == (0.0,0.0)
        assert cobj._powi((0.0,1.0),2) == (-1.0,0.0)
        c = cobj.W_ComplexObject(0.0,1.0)
        p = cobj.W_ComplexObject(2.0,0.0)
        r = cobj.pow__Complex_Complex_ANY(self.space,c,p,self.space.wrap(None))
        assert r.realval == -1.0
        assert r.imagval == 0.0


class AppTestAppComplexTest:
    def setup_class(cls):
        # XXX these tests probably copied directly from CPython
        # please port them to pypy style :-/
        cls.w_helper = cls.space.appexec([], """
            ():
                import sys
                sys.path.append(%r)
                import helper
                return helper
        """ % (str(py.path.local(__file__).dirpath())))

    def test_div(self):
        h = self.helper
        from random import random
        # XXX this test passed but took waaaaay to long
        # look at dist/lib-python/modified-2.5.2/test/test_complex.py
        #simple_real = [float(i) for i in xrange(-5, 6)]
        simple_real = [-2.0, 0.0, 1.0]
        simple_complex = [complex(x, y) for x in simple_real for y in simple_real]
        for x in simple_complex:
            for y in simple_complex:
                h.check_div(x, y)

        # A naive complex division algorithm (such as in 2.0) is very prone to
        # nonsense errors for these (overflows and underflows).
        h.check_div(complex(1e200, 1e200), 1+0j)
        h.check_div(complex(1e-200, 1e-200), 1+0j)

        # Just for fun.
        for i in xrange(100):
            h.check_div(complex(random(), random()),
                           complex(random(), random()))

        h.raises(ZeroDivisionError, complex.__div__, 1+1j, 0+0j)
        # FIXME: The following currently crashes on Alpha
        # raises(OverflowError, pow, 1e200+1j, 1e200+1j)

    def test_truediv(self):
        h = self.helper
        h.assertAlmostEqual(complex.__truediv__(2+0j, 1+1j), 1-1j)
        raises(ZeroDivisionError, complex.__truediv__, 1+1j, 0+0j)

    def test_floordiv(self):
        h = self.helper
        h.assertAlmostEqual(complex.__floordiv__(3+0j, 1.5+0j), 2)
        raises(ZeroDivisionError, complex.__floordiv__, 3+0j, 0+0j)

    def test_coerce(self):
        h = self.helper
        h.raises(OverflowError, complex.__coerce__, 1+1j, 1L<<10000)

    def test_richcompare(self):
        h = self.helper
        h.raises(OverflowError, complex.__eq__, 1+1j, 1L<<10000)
        h.assertEqual(complex.__lt__(1+1j, None), NotImplemented)
        h.assertIs(complex.__eq__(1+1j, 1+1j), True)
        h.assertIs(complex.__eq__(1+1j, 2+2j), False)
        h.assertIs(complex.__ne__(1+1j, 1+1j), False)
        h.assertIs(complex.__ne__(1+1j, 2+2j), True)
        h.raises(TypeError, complex.__lt__, 1+1j, 2+2j)
        h.raises(TypeError, complex.__le__, 1+1j, 2+2j)
        h.raises(TypeError, complex.__gt__, 1+1j, 2+2j)
        h.raises(TypeError, complex.__ge__, 1+1j, 2+2j)

    def test_mod(self):
        h = self.helper
        raises(ZeroDivisionError, (1+1j).__mod__, 0+0j)

        a = 3.33+4.43j
        try:
            a % 0
        except ZeroDivisionError:
            pass
        else:
            self.fail("modulo parama can't be 0")

    def test_divmod(self):
        h = self.helper
        raises(ZeroDivisionError, divmod, 1+1j, 0+0j)

    def test_pow(self):
        h = self.helper
        h.assertAlmostEqual(pow(1+1j, 0+0j), 1.0)
        h.assertAlmostEqual(pow(0+0j, 2+0j), 0.0)
        raises(ZeroDivisionError, pow, 0+0j, 1j)
        h.assertAlmostEqual(pow(1j, -1), 1/1j)
        h.assertAlmostEqual(pow(1j, 200), 1)
        raises(ValueError, pow, 1+1j, 1+1j, 1+1j)

        a = 3.33+4.43j
        h.assertEqual(a ** 0j, 1)
        h.assertEqual(a ** 0.+0.j, 1)

        h.assertEqual(3j ** 0j, 1)
        h.assertEqual(3j ** 0, 1)

        try:
            0j ** a
        except ZeroDivisionError:
            pass
        else:
            self.fail("should fail 0.0 to negative or complex power")

        try:
            0j ** (3-2j)
        except ZeroDivisionError:
            pass
        else:
            self.fail("should fail 0.0 to negative or complex power")

        # The following is used to exercise certain code paths
        h.assertEqual(a ** 105, a ** 105)
        h.assertEqual(a ** -105, a ** -105)
        h.assertEqual(a ** -30, a ** -30)

        h.assertEqual(0.0j ** 0, 1)

        b = 5.1+2.3j
        h.raises(ValueError, pow, a, b, 0)

    def test_boolcontext(self):
        from random import random
        h = self.helper
        for i in xrange(100):
            assert complex(random() + 1e-6, random() + 1e-6)
        assert not complex(0.0, 0.0)

    def test_conjugate(self):
        h = self.helper
        h.assertClose(complex(5.3, 9.8).conjugate(), 5.3-9.8j)

    def test_constructor(self):
        h = self.helper
        class OS:
            def __init__(self, value): self.value = value
            def __complex__(self): return self.value
        class NS(object):
            def __init__(self, value): self.value = value
            def __complex__(self): return self.value
        h.assertEqual(complex(OS(1+10j)), 1+10j)
        h.assertEqual(complex(NS(1+10j)), 1+10j)
        h.raises(TypeError, complex, OS(None))
        h.raises(TypeError, complex, NS(None))

        h.assertAlmostEqual(complex("1+10j"), 1+10j)
        h.assertAlmostEqual(complex(10), 10+0j)
        h.assertAlmostEqual(complex(10.0), 10+0j)
        h.assertAlmostEqual(complex(10L), 10+0j)
        h.assertAlmostEqual(complex(10+0j), 10+0j)
        h.assertAlmostEqual(complex(1,10), 1+10j)
        h.assertAlmostEqual(complex(1,10L), 1+10j)
        h.assertAlmostEqual(complex(1,10.0), 1+10j)
        h.assertAlmostEqual(complex(1L,10), 1+10j)
        h.assertAlmostEqual(complex(1L,10L), 1+10j)
        h.assertAlmostEqual(complex(1L,10.0), 1+10j)
        h.assertAlmostEqual(complex(1.0,10), 1+10j)
        h.assertAlmostEqual(complex(1.0,10L), 1+10j)
        h.assertAlmostEqual(complex(1.0,10.0), 1+10j)
        h.assertAlmostEqual(complex(3.14+0j), 3.14+0j)
        h.assertAlmostEqual(complex(3.14), 3.14+0j)
        h.assertAlmostEqual(complex(314), 314.0+0j)
        h.assertAlmostEqual(complex(314L), 314.0+0j)
        h.assertAlmostEqual(complex(3.14+0j, 0j), 3.14+0j)
        h.assertAlmostEqual(complex(3.14, 0.0), 3.14+0j)
        h.assertAlmostEqual(complex(314, 0), 314.0+0j)
        h.assertAlmostEqual(complex(314L, 0L), 314.0+0j)
        h.assertAlmostEqual(complex(0j, 3.14j), -3.14+0j)
        h.assertAlmostEqual(complex(0.0, 3.14j), -3.14+0j)
        h.assertAlmostEqual(complex(0j, 3.14), 3.14j)
        h.assertAlmostEqual(complex(0.0, 3.14), 3.14j)
        h.assertAlmostEqual(complex("1"), 1+0j)
        h.assertAlmostEqual(complex("1j"), 1j)
        h.assertAlmostEqual(complex(),  0)
        h.assertAlmostEqual(complex("-1"), -1)
        h.assertAlmostEqual(complex("+1"), +1)

        class complex2(complex): pass
        h.assertAlmostEqual(complex(complex2(1+1j)), 1+1j)
        h.assertAlmostEqual(complex(real=17, imag=23), 17+23j)
        h.assertAlmostEqual(complex(real=17+23j), 17+23j)
        h.assertAlmostEqual(complex(real=17+23j, imag=23), 17+46j)
        h.assertAlmostEqual(complex(real=1+2j, imag=3+4j), -3+5j)

        c = 3.14 + 1j
        assert complex(c) is c
        del c

        h.raises(TypeError, complex, "1", "1")
        h.raises(TypeError, complex, 1, "1")

        h.assertEqual(complex("  3.14+J  "), 3.14+1j)
        #h.assertEqual(complex(unicode("  3.14+J  ")), 3.14+1j)

        # SF bug 543840:  complex(string) accepts strings with \0
        # Fixed in 2.3.
        h.raises(ValueError, complex, '1+1j\0j')

        h.raises(TypeError, int, 5+3j)
        h.raises(TypeError, long, 5+3j)
        h.raises(TypeError, float, 5+3j)
        h.raises(ValueError, complex, "")
        h.raises(TypeError, complex, None)
        h.raises(ValueError, complex, "\0")
        h.raises(TypeError, complex, "1", "2")
        h.raises(TypeError, complex, "1", 42)
        h.raises(TypeError, complex, 1, "2")
        h.raises(ValueError, complex, "1+")
        h.raises(ValueError, complex, "1+1j+1j")
        h.raises(ValueError, complex, "--")
#        if x_test_support.have_unicode:
#            h.raises(ValueError, complex, unicode("1"*500))
#            h.raises(ValueError, complex, unicode("x"))
#
        class EvilExc(Exception):
            pass

        class evilcomplex:
            def __complex__(self):
                raise EvilExc

        h.raises(EvilExc, complex, evilcomplex())

        class float2:
            def __init__(self, value):
                self.value = value
            def __float__(self):
                return self.value

        h.assertAlmostEqual(complex(float2(42.)), 42)
        h.assertAlmostEqual(complex(real=float2(17.), imag=float2(23.)), 17+23j)
        h.raises(TypeError, complex, float2(None))

    def test_hash(self):
        h = self.helper
        for x in xrange(-30, 30):
            h.assertEqual(hash(x), hash(complex(x, 0)))
            x /= 3.0    # now check against floating point
            h.assertEqual(hash(x), hash(complex(x, 0.)))

    def test_abs(self):
        h = self.helper
        nums = [complex(x/3., y/7.) for x in xrange(-9,9) for y in xrange(-9,9)]
        for num in nums:
            h.assertAlmostEqual((num.real**2 + num.imag**2)  ** 0.5, abs(num))

    def test_complex_subclass_ctr(self):
        import sys
        class j(complex):
            pass
        assert j(100 + 0j) == 100 + 0j
        assert isinstance(j(100),j)
        assert j(100L + 0j) == 100 + 0j
        assert j("100 + 0j") == 100 + 0j
        x = j(1+0j)
        x.foo = 42
        assert x.foo == 42
        assert type(complex(x)) == complex
    
    def test_overflow(self):
        h = self.helper
        raises(ValueError, complex, unicode("1"*500))
        
    def test_repr(self):
        h = self.helper
        h.assertEqual(repr(1+6j), '(1+6j)')
        h.assertEqual(repr(1-6j), '(1-6j)')

        h.assertNotEqual(repr(-(1+0j)), '(-1+-0j)')

    def test_neg(self):
        h = self.helper
        h.assertEqual(-(1+6j), -1-6j)

    def test_file(self):
        h = self.helper
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
            h.assertEqual(fo.read(), "%s %s\n" % (a, b))
        finally:
            if (fo is not None) and (not fo.closed):
                fo.close()
            try:
                os.remove(pth)
            except (OSError, IOError):
                pass

    def test_convert(self):
        raises(TypeError, int, 1+1j)
        raises(TypeError, float, 1+1j)
