import numpy


def mean(a):
    if not hasattr(a, "mean"):
        a = numpy.array(a)
    return a.mean()