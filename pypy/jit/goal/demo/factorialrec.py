import time


def f(n):
    if n > 1:
        return n * f(n-1)
    else:
        return 1

import pypyjit
pypyjit.enable(f.func_code)

print f(7)
