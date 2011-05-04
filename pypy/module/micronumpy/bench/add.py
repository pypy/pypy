
import numpy

def f():
    a = numpy.zeros(1000000)
    a = a + a + a + a + a
    if hasattr(a, 'force'):
        a.force()

f()
