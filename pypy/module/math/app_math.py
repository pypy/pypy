def factorial(x):
    """Find x!."""
    if isinstance(x, float):
        fl = int(x)
        if fl != x:
            raise ValueError("float arguments must be integral")
        x = fl
    if x < 0:
        raise ValueError("x must be >= 0")
    res = 1
    for i in range(1, x + 1):
        res *= i
    return res
