import sys
try:
    from _operator import index
except ImportError:
    pass      # for tests only

def factorial(n, /):
    """factorial(n, /) -> int

    Find n!. Raise a ValueError if n is negative or non-integral."""
    n = index(n)
    if n > sys.maxsize:
        raise OverflowError("Too large for a factorial")

    if n <= 100:
        if n < 0:
            raise ValueError("n must be a non-negative integer")
        res = 1
        for i in range(2, n + 1):
            res *= i
        return res

    # Experimentally this gap seems good
    gap = max(100, n >> 7)
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

    res, _, shift = _fac1(n)
    return res << shift


def isqrt(n, /):
    """
    Return the integer part of the square root of the input.
    """
    n = index(n)

    if n < 0:
        raise ValueError("isqrt() argument must be nonnegative")
    if n == 0:
        return 0

    c = (n.bit_length() - 1) // 2
    a = 1
    d = 0
    for s in reversed(range(c.bit_length())):
        # Loop invariant: (a-1)**2 < (n >> 2*(c - d)) < (a+1)**2
        e = d
        d = c >> s
        a = (a << d - e - 1) + (n >> 2*c - e - d + 1) // a

    return a - (a*a > n)

def prod(iterable, /, *, start=1):
    """
    Calculate the product of all the elements in the input iterable.

    The default start value for the product is 1.

    When the iterable is empty, return the start value.  This function is
    intended specifically for use with numeric values and may reject
    non-numeric types.
    """
    res = start
    for x in iterable:
        res = res * x
    return res

def sumprod(p, q, /):
    """
    Return the sum of products of values from two iterables p and q.

    Roughly equivalent to:

        sum(itertools.starmap(operator.mul, zip(p, q, strict=True)))

    Unlike CPython, this does not use extended precision for the
    intermediate products and sums; it matches the naive recipe above.
    """
    p_it = iter(p)
    q_it = iter(q)
    total = 0
    while True:
        try:
            p_i = next(p_it)
        except StopIteration:
            p_stopped = True
        else:
            p_stopped = False
        try:
            q_i = next(q_it)
        except StopIteration:
            q_stopped = True
        else:
            q_stopped = False
        if p_stopped != q_stopped:
            raise ValueError('Inputs are not the same length')
        if p_stopped:
            # both iterables are exhausted
            return total
        total += p_i * q_i

def comb(n, k, /):
    """
    Number of ways to choose k items from n items without repetition and without order.

    Evaluates to n! / (k! * (n - k)!) when k <= n and evaluates
    to zero when k > n.

    Also called the binomial coefficient because it is equivalent
    to the coefficient of k-th term in polynomial expansion of the
    expression (1 + x)**n.

    Raises TypeError if either of the arguments are not integers.
    Raises ValueError if either of the arguments are negative.
    """
    n = index(n)
    k = index(k)

    if n < 0:
        raise ValueError("n must be a non-negative integer")
    if k < 0:
        raise ValueError("k must be a non-negative integer")
    if k > n:
        return 0

    k = min(k, n-k)
    if k == 0:
        return 1

    num, den = n, 1
    for i in range(1, k):
        num *= n - i
        den *= i + 1
        # reduce the fraction occasionally, but not after every multiplication
        if i & 15 == 0:
            num //= den
            den = 1

    return num // den

def perm(n, k=None, /):
    """
    Number of ways to choose k items from n items without repetition and with order.

    Evaluates to n! / (n - k)! when k <= n and evaluates
    to zero when k > n.

    If k is not specified or is None, then k defaults to n
    and the function returns n!.

    Raises TypeError if either of the arguments are not integers.
    Raises ValueError if either of the arguments are negative.
    """

    n = index(n)
    if k is None:
        k = n
    else:
        k = index(k)

    if n < 0:
        raise ValueError("n must be a non-negative integer")
    if k < 0:
        raise ValueError("k must be a non-negative integer")
    if k > n:
        return 0

    if k <= 100:
        res = 1
        for x in range(n, n - k, -1):
            res *= x
        return res

    gap = max(100, k >> 7)
    def _prod_range(low, high):
        if low + gap >= high:
            t = 1
            for i in range(low, high):
                t *= i
            return t

        mid = (low + high) >> 1
        return _prod_range(low, mid) * _prod_range(mid, high)

    return _prod_range(n - k + 1, n + 1)


def lcm(*integers):
    import math
    if not integers:
        return 1
    # every argument must be validated via index(), even once the
    # running result is already known to be 0 - matches CPython's
    # math_lcm(), which always calls PyNumber_Index(args[i]) before
    # checking "res == zero"
    res = abs(index(integers[0]))
    for i in range(1, len(integers)):
        v = abs(index(integers[i]))
        if res == 0:
            continue
        if v == 0:
            res = 0
            continue
        res = res // math.gcd(res, v) * v
    return res
