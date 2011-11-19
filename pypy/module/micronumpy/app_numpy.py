import math

import numpypy


inf = float("inf")
e = math.e

def average(a):
    # This implements a weighted average, for now we don't implement the
    # weighting, just the average part!
    return mean(a)

def mean(a):
    if not hasattr(a, "mean"):
        a = numpypy.array(a)
    return a.mean()
