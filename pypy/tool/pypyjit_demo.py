
import time
l = []

for i in range(100):
    print i
    t0 = time.time()
    exec """
def k(a, b, c):
    pass

def g(a, b, c):
    k(a, b + 1, c + 2)
    k(a, b + 1, c + 2)
    k(a, b + 1, c + 2)
    k(a, b + 1, c + 2)
    k(a, b + 1, c + 2)

def f(i):
    g(i, i + 1, i + 2)
    g(i, i + 1, i + 2)
    g(i, i + 1, i + 2)
    g(i, i + 1, i + 2)
    g(i, i + 1, i + 2)
    g(i, i + 1, i + 2)
for i in range(1000):
    f(i)
"""
    l.append(time.time() - t0)

print l
