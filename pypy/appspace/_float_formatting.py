import math

# from the excessive effort department, routines for printing floating
# point numbers from

# "Printing Floating-Point Numbers Quickly and Accurately" by Burger &
# Dybvig, Proceedings of the SIGPLAN '96 Conference on Programming
# Language Design and Implementation.

# The paper contains scheme code which has been specialized for IEEE
# doubles and converted into Python by Michael Hudson.

# XXX unfortunately, we need the fixed-format output routines, the source
# for which is not included in the paper... for now, just put up with
# occasionally incorrectly rounded final digits.  I'll get to it.

# XXX should run this at interpreter level, really....

def decode_float(f):
    """decode_float(float) -> int, int

    Return (m, e), the mantissa and exponent respectively of
    f (assuming f is an IEEE double), i.e. f == m * 2**e and
    2**52 <= m < 2**53."""
    m, e = math.frexp(f)
    m = long(m*2.0**53)
    e -= 53
    return m, e

def decompose(f):
    """decompose(float) -> int, int, int, int

    Return r, s, m_plus, m_minus for f, in the terms of
    Burger and Dybvig's paper (see Table 1).

    To spell this out: f = r/s, (r+m+)/s is halfway to the
    next largest floating point number, (r-m-) halfway to
    the next smallest."""
    m, e = decode_float(f)
    if e >= 0:
        if not m != 2**52:
            be = 2**e
            return m*be*2, 2, be, be
        else:
            be = 2**e
            be1 = 2*be
            return m*be1*2, 4, be1, be
    else:
        if e == -1075 or m != 2**52:
            return m*2, 2**(-e+1), 1, 1
        else:
            return m*4, 2**(-e+2), 2, 1


def flonum2digits(f):
    """flonum2digits(float) -> [int], int

    Given a float f return [d1, ..., dn], k such that

        0.[d1][d2]...[dn] * 10**k

    is the shortest decimal representation that will
    reproduce f when read in by a correctly rounding input
    routine (under any strategy for breaking ties)."""
    
    assert f >= 0
    if f == 0.0:
        return ['0'], 1

    # See decompose's docstring for what these mean.
    r, s, m_plus, m_minus = decompose(f)

    # k is the index, relative to the radix point of the
    # most-significant non-zero digit of the infinite
    # decimal expansion of f.  This calculation has the
    # potential to underestimate by one (handled below).
    k = long(math.ceil(math.log10(f) - 1e-10))

    if k >= 0:
        s *= 10 ** k
    else:
        scale = 10 ** -k
        r *= scale
        m_plus *= scale
        m_minus *= scale

    # Check that we got k right above.
    if r + m_plus > s:
        s *= 10
        k += 1

    # Generate the digits.
    rr = []
    while 1:
        d, r = divmod(r*10, s)
        m_plus *= 10
        m_minus *= 10
        tc1 = r < m_minus
        tc2 = (r + m_plus) > s
        if tc2:
            rr.append(d+1)
        else:
            rr.append(d)
        if tc1 or tc2:
            break
        
    assert max(rr) < 10
    assert min(rr) >= 0

    return map(str, rr), k
