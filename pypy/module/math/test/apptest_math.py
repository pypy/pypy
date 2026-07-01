import pytest
import math
import sys

def test_product():
    assert math.prod([1, 2, 3]) == 6
    assert math.prod([1, 2, 3], start=0.5) == 3.0
    assert math.prod([]) == 1.0
    assert math.prod([], start=5) == 5

def test_julians_weird_test_prod():
    class A:
        def __mul__(self, other):
                return 12
        def __imul__(self, other):
                return 13

    # check that the implementation doesn't use *=
    assert math.prod([1, 2], start=A())

def test_more_weird_prod():
    start = [4]
    assert math.prod([2], start=start) == [4, 4]
    assert start == [4]
    start =  object()
    assert math.prod([], start=start) is start


def test_sumprod():
    from math import sumprod, inf, nan, isnan
    # basics
    assert sumprod([], []) == 0
    assert sumprod([1, 2, 3], [4, 5, 6]) == 32
    assert sumprod([1.0, 2.0], [3.0, 4.0]) == 11.0
    # exact big ints
    assert sumprod([10**20], [1]) == 10**20
    assert sumprod([10**7] * 10**4, [10**7] * 10**4) == 10**18
    # signature / non-iterable -> TypeError
    pytest.raises(TypeError, sumprod)
    pytest.raises(TypeError, sumprod, [])
    pytest.raises(TypeError, sumprod, [], [], [])
    pytest.raises(TypeError, sumprod, None, [10])
    pytest.raises(TypeError, sumprod, [10], None)
    # uneven lengths -> ValueError
    pytest.raises(ValueError, sumprod, [10, 20], [30])
    pytest.raises(ValueError, sumprod, [10], [20, 30])
    # overflow converting a huge int to float during the product
    pytest.raises(OverflowError, sumprod, [10**1000], [1.0])
    # error propagation from the iterator
    def raise_after(n):
        for i in range(n):
            yield i
        raise RuntimeError
    pytest.raises(RuntimeError, sumprod, range(10), raise_after(5))
    # error propagation from multiplication and addition
    class BadMultiply:
        def __mul__(self, other): raise RuntimeError
        __rmul__ = __mul__
    pytest.raises(RuntimeError, sumprod, [1, BadMultiply(), 3], [1, 2, 3])
    pytest.raises(TypeError, sumprod, ['abc', 3], [5, 10])
    # special values match the naive recipe
    assert sumprod([10.1, inf], [20.2, 30.3]) == inf
    assert sumprod([10.1, -inf], [20.2, 30.3]) == -inf
    assert isnan(sumprod([10.1, nan], [20.2, 30.3]))


def test_comb():
    from math import comb, factorial

    assert comb(10, 11) == 0
    for n in range(5):
        for k in range(n + 1):
            assert comb(n, k) == factorial(n) // (factorial(k) * factorial(n - k))

    class A:
        def __index__(self):
            return 4

    assert comb(A(), 2) == comb(4, 2)


def test_perm():
    from math import perm, factorial

    assert perm(10, 11) == 0

    for n in range(5):
        for k in range(n + 1):
            assert perm(n, k) == factorial(n) // factorial(n - k)

    class A:
        def __index__(self):
            return 4

    assert perm(A(), 2) == perm(4, 2)

def test_hypot_many_args():
    from math import hypot
    args = math.e, math.pi, math.sqrt(2.0), math.gamma(3.5), math.sin(2.1), 1e48, 2e-47
    for i in range(len(args)+1):
        assert round(
            hypot(*args[:i]) - math.sqrt(sum(s**2 for s in args[:i])), 7) == 0


def test_dist():
    from math import dist
    assert dist((1.0, 2.0, 3.0), (4.0, 2.0, -1.0)) == 5.0
    assert dist((1, 2, 3), (4, 2, -1)) == 5.0
    with pytest.raises(TypeError):
        math.dist(p=(1, 2, 3), q=(2, 3, 4)) # posonly args :-/

def test_nextafter():
    INF = float("inf")
    NAN = float("nan")
    assert math.nextafter(4503599627370496.0, -INF) == 4503599627370495.5
    assert math.nextafter(4503599627370496.0, INF) == 4503599627370497.0
    assert math.nextafter(9223372036854775808.0, 0.0) == 9223372036854774784.0
    assert math.nextafter(-9223372036854775808.0, 0.0) == -9223372036854774784.0

    # around 1.0
    assert math.nextafter(1.0, -INF) == float.fromhex('0x1.fffffffffffffp-1')
    assert math.nextafter(1.0, INF)== float.fromhex('0x1.0000000000001p+0')

    # x == y: y is returned
    assert math.nextafter(2.0, 2.0) == 2.0

    # around 0.0
    smallest_subnormal = sys.float_info.min * sys.float_info.epsilon
    assert math.nextafter(+0.0, INF) == smallest_subnormal
    assert math.nextafter(-0.0, INF) == smallest_subnormal
    assert math.nextafter(+0.0, -INF) == -smallest_subnormal
    assert math.nextafter(-0.0, -INF) == -smallest_subnormal

    # around infinity
    largest_normal = sys.float_info.max
    assert math.nextafter(INF, 0.0) == largest_normal
    assert math.nextafter(-INF, 0.0) == -largest_normal
    assert math.nextafter(largest_normal, INF) == INF
    assert math.nextafter(-largest_normal, -INF) == -INF

    # NaN
    assert math.isnan(math.nextafter(NAN, 1.0))
    assert math.isnan(math.nextafter(1.0, NAN))
    assert math.isnan(math.nextafter(NAN, NAN))

def test_ulp():
    INF = float("inf")
    NAN = float("nan")
    FLOAT_MAX = sys.float_info.max
    assert math.ulp(1.0) == sys.float_info.epsilon
    assert math.ulp(2 ** 52) == 1.0
    assert math.ulp(2 ** 53) == 2.0
    assert math.ulp(2 ** 64) == 4096.0

    assert math.ulp(0.0) == sys.float_info.min * sys.float_info.epsilon
    assert math.ulp(FLOAT_MAX) == FLOAT_MAX - math.nextafter(FLOAT_MAX, -INF)

    # special cases
    assert math.ulp(INF) == INF
    assert math.isnan(math.ulp(math.nan))

    # negative number: ulp(-x) == ulp(x)
    for x in (0.0, 1.0, 2 ** 52, 2 ** 64, INF):
        assert math.ulp(-x) == math.ulp(x)

def test_factorial_raises():
    with pytest.raises(TypeError) as e:
        math.factorial(1.2)
    assert e.value.args[0] == "'float' object cannot be interpreted as an integer"

@pytest.mark.skipif(sys.maxsize <= 2**31 - 1, reason="bigint on 32-bytes is slow")
def test_factorial_values():
    def ref(n):
        r = 1
        for i in range(2, n + 1):
            r *= i
        return r
    for x in range(1000):
        assert math.factorial(x) == ref(x)

@pytest.mark.skipif(not hasattr(sys, 'pypy_translation_info'), reason='requires translated PyPy')
def test_signatures():
    import inspect
    assert str(inspect.signature(math.factorial)) == '(n, /)'
    assert str(inspect.signature(math.isqrt)) == '(n, /)'
    assert str(inspect.signature(math.gcd)) == '(*integers)'
    assert str(inspect.signature(math.lcm)) == '(*integers)'

