def raises(excp, func, *args):
    try:
        func(*args)
        assert 1 == 0
    except excp:pass

def assertEqual(a, b):
    assert a == b

def assertNotEqual(a, b):
    assert a != b

def assertIs(a, b):
    assert a is b

# complex specific tests

EPS = 1e-9

def assertAlmostEqual(a, b):
    if isinstance(a, complex):
        if isinstance(b, complex):
            assert a.real - b.real < EPS
            assert a.imag - b.imag < EPS
        else:
            assert a.real - b < EPS
            assert a.imag < EPS
    else:
        if isinstance(b, complex):
            assert a - b.real < EPS
            assert b.imag < EPS
        else:
            assert a - b < EPS

def assertCloseAbs(x, y, eps=1e-9):
    """Return true iff floats x and y "are close\""""
    # put the one with larger magnitude second
    if abs(x) > abs(y):
        x, y = y, x
    if y == 0:
        return abs(x) < eps
    if x == 0:
        return abs(y) < eps
    # check that relative difference < eps
    assert abs((x-y)/y) < eps

def assertClose(x, y, eps=1e-9):
    """Return true iff complexes x and y "are close\""""
    assertCloseAbs(x.real, y.real, eps)
    assertCloseAbs(x.imag, y.imag, eps)


def check_div(x, y):
    """Compute complex z=x*y, and check that z/x==y and z/y==x."""
    z = x * y
    if x != 0:
        q = z / x
        assertClose(q, y)
        q = z.__div__(x)
        assertClose(q, y)
        q = z.__truediv__(x)
        assertClose(q, y)
    if y != 0:
        q = z / y
        assertClose(q, x)
        q = z.__div__(y)
        assertClose(q, x)
        q = z.__truediv__(y)
        assertClose(q, x)
