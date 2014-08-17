def factorial(x):
    """factorial(x) -> Integral

    "Find x!. Raise a ValueError if x is negative or non-integral."""
    if isinstance(x, float):
        fl = int(x)
        if fl != x:
            raise ValueError("float arguments must be integral")
        x = fl

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
