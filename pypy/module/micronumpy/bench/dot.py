import time

try:
    import numpypy
except ImportError:
    pass

import numpy

def get_matrix():
    import random
    n = 502
    x = numpy.zeros((n,n), dtype=numpy.float64)
    for i in range(n):
        for j in range(n):
            x[i][j] = random.random()
    return x

def main():
    x = get_matrix()
    y = get_matrix()
    a = time.time()
    #z = numpy.dot(x, y)  # uses numpy possibly-blas-lib dot
    z = numpy.core.multiarray.dot(x, y)  # uses strictly numpy C dot
    b = time.time()
    print '%.2f seconds' % (b-a)

main()
