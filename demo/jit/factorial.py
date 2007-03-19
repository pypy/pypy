import time


def f(n):
    r = 1
    while n > 1:
        r *= n
        n -= 1
    return r

import pypyjit
pypyjit.enable(f.func_code)

print f(7)
