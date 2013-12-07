def factorial(x):
    """Find x!."""
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
    
    #Experimentally this gap seems good
    gap = max(100, x>>7)
    def _fac(low, high):
        if low+gap >= high:
            t = 1
            for i in range(low, high):
                t *= i
            return t
        
        mid = (low + high) >> 1
        return _fac(low, mid) * _fac(mid, high)
    
    return _fac(1, x+1)
