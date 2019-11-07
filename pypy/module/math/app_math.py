import sys
try:
    from _operator import index
except ImportError:
    pass      # for tests only

def factorial(x):
    """factorial(x) -> Integral

    "Find x!. Raise a ValueError if x is negative or non-integral."""
    if isinstance(x, float):
        fl = int(x)
        if fl != x:
            raise ValueError("float arguments must be integral")
        x = fl
    if x > sys.maxsize:
        raise OverflowError("Too large for a factorial")

    if x <= 100:
        if x < 0:
            raise ValueError("x must be >= 0")
        res = 1
        for i in range(2, x + 1):
            res *= i
        return res

    # Experimentally this gap seems good
    gap = max(100, x >> 7)
    def _fac_odd(low, high):
        if low + gap >= high:
            t = 1
            for i in range(low, high, 2):
                t *= i
            return t

        mid = ((low + high) >> 1) | 1
        return _fac_odd(low, mid) * _fac_odd(mid, high)

    def _fac1(x):
        if x <= 2:
            return 1, 1, x - 1
        x2 = x >> 1
        f, g, shift = _fac1(x2)
        g *= _fac_odd((x2 + 1) | 1, x + 1)
        return (f * g, g, shift + x2)

    res, _, shift = _fac1(x)
    return res << shift


def remainder(x, y):
    """Difference between x and the closest integer multiple of y.

    Return x - n*y where n*y is the closest integer multiple of y.
    In the case where x is exactly halfway between two multiples of
    y, the nearest even value of n is used. The result is always exact."""

    from math import copysign, fabs, fmod, isfinite, isinf, isnan, nan

    x = float(x)
    y = float(y)

    # Deal with most common case first.
    if isfinite(x) and isfinite(y):
        if y == 0.0:
            # return nan
            # Merging the logic from math_2 in CPython's mathmodule.c
            # nan returned and x and y both not nan -> domain error
            raise ValueError("math domain error")
        
        absx = fabs(x)
        absy = fabs(y)
        m = fmod(absx, absy)

        # Warning: some subtlety here. What we *want* to know at this point is
        # whether the remainder m is less than, equal to, or greater than half
        # of absy. However, we can't do that comparison directly because we
        # can't be sure that 0.5*absy is representable (the mutiplication
        # might incur precision loss due to underflow). So instead we compare
        # m with the complement c = absy - m: m < 0.5*absy if and only if m <
        # c, and so on. The catch is that absy - m might also not be
        # representable, but it turns out that it doesn't matter:
        # - if m > 0.5*absy then absy - m is exactly representable, by
        #     Sterbenz's lemma, so m > c
        # - if m == 0.5*absy then again absy - m is exactly representable
        #     and m == c
        # - if m < 0.5*absy then either (i) 0.5*absy is exactly representable,
        #     in which case 0.5*absy < absy - m, so 0.5*absy <= c and hence m <
        #     c, or (ii) absy is tiny, either subnormal or in the lowest normal
        #     binade. Then absy - m is exactly representable and again m < c.

        c = absy - m
        if m < c:
            r = m
        elif m > c:
            r = -c
        else:
            # Here absx is exactly halfway between two multiples of absy,
            # and we need to choose the even multiple. x now has the form
            #     absx = n * absy + m
            # for some integer n (recalling that m = 0.5*absy at this point).
            # If n is even we want to return m; if n is odd, we need to
            # return -m.
            # So
            #     0.5 * (absx - m) = (n/2) * absy
            # and now reducing modulo absy gives us:
            #                                     | m, if n is odd
            #     fmod(0.5 * (absx - m), absy) = |
            #                                     | 0, if n is even
            # Now m - 2.0 * fmod(...) gives the desired result: m
            # if n is even, -m if m is odd.
            # Note that all steps in fmod(0.5 * (absx - m), absy)
            # will be computed exactly, with no rounding error
            # introduced.
            assert m == c
            r = m - 2.0 * fmod(0.5 * (absx - m), absy)
        return copysign(1.0, x) * r
    
    # Special values.
    if isnan(x):
        return x
    if isnan(y):
        return y
    if isinf(x):
        # return nan
        # Merging the logic from math_2 in CPython's mathmodule.c
        # nan returned and x and y both not nan -> domain error
        raise ValueError("math domain error")
    assert isinf(y)
    return x
 