from __future__ import with_statement
from pypy.conftest import gettestobjspace
import os


class AppTestCMath:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['cmath'])

    def test_sign(self):
        z = eval("-0j")
        assert z == -0j
        assert math.copysign(1., z.real) == 1.
        assert math.copysign(1., z.imag) == -1.

    def test_sqrt(self):
        import cmath, math
        assert cmath.sqrt(3+4j) == 2+1j
        z = cmath.sqrt(-0j)
        assert math.copysign(1., z.real) == 1.
        assert math.copysign(1., z.imag) == -1.
        dbl_min = 2.2250738585072014e-308
        z = cmath.sqrt((dbl_min * 0.00000000000001) + 0j)
        assert abs(z.real - 1.49107189843e-161) < 1e-170
        assert z.imag == 0.0

    def test_acos(self):
        import cmath
        assert cmath.acos(0.5+0j) == 1.0471975511965979+0j


def parse_testfile(fname):
    """Parse a file with test values

    Empty lines or lines starting with -- are ignored
    yields id, fn, arg_real, arg_imag, exp_real, exp_imag
    """
    fname = os.path.join(os.path.dirname(__file__), fname)
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


def test_specific_values(space):
    #if not float.__getformat__("double").startswith("IEEE"):
    #    return

    def rect_complex(z):
        """Wrapped version of rect that accepts a complex number instead of
        two float arguments."""
        return cmath.rect(z.real, z.imag)

    def polar_complex(z):
        """Wrapped version of polar that returns a complex number instead of
        two floats."""
        return complex(*polar(z))

    for id, fn, ar, ai, er, ei, flags in parse_testfile(test_file):
        w_arg = space.newcomplex(ar, ai)
        w_expected = space.newcomplex(er, ei)
        if fn == 'rect':
            function = rect_complex
        elif fn == 'polar':
            function = polar_complex
        else:
            function = getattr(cmath, fn)
        if 'divide-by-zero' in flags or 'invalid' in flags:
            try:
                actual = function(arg)
            except ValueError:
                continue
            else:
                self.fail('ValueError not raised in test '
                      '{}: {}(complex({!r}, {!r}))'.format(id, fn, ar, ai))

        if 'overflow' in flags:
            try:
                actual = function(arg)
            except OverflowError:
                continue
            else:
                self.fail('OverflowError not raised in test '
                      '{}: {}(complex({!r}, {!r}))'.format(id, fn, ar, ai))

        actual = function(arg)

        if 'ignore-real-sign' in flags:
            actual = complex(abs(actual.real), actual.imag)
            expected = complex(abs(expected.real), expected.imag)
        if 'ignore-imag-sign' in flags:
            actual = complex(actual.real, abs(actual.imag))
            expected = complex(expected.real, abs(expected.imag))

        # for the real part of the log function, we allow an
        # absolute error of up to 2e-15.
        if fn in ('log', 'log10'):
            real_abs_err = 2e-15
        else:
            real_abs_err = 5e-323

        error_message = (
            '{}: {}(complex({!r}, {!r}))\n'
            'Expected: complex({!r}, {!r})\n'
            'Received: complex({!r}, {!r})\n'
            'Received value insufficiently close to expected value.'
            ).format(id, fn, ar, ai,
                 expected.real, expected.imag,
                 actual.real, actual.imag)
        self.rAssertAlmostEqual(expected.real, actual.real,
                                    abs_err=real_abs_err,
                                    msg=error_message)
        self.rAssertAlmostEqual(expected.imag, actual.imag,
                                    msg=error_message)
