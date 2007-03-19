import time


ZERO = 0

def f1(n):
    "Arbitrary test function."
    i = 0
    x = 1
    while i<n:
        j = 0   #ZERO
        while j<=i:
            j = j + 1
            x = x + (i&j)
        i = i + 1
    return x


try:
    import pypyjit
except ImportError:
    print "No jit"
else:
    pypyjit.enable(f1.func_code)

res = f1(2117)
print res
N = 5
start = time.time()
for i in range(N):
    assert f1(2117) == res
end = time.time()

print '%d iterations, time per iteration: %s' % (N, (end-start)/N)
