
try:
<<<<<<< local
    import numpy
    a = numpy.array(range(10))
    b = a + a + a
    print b[3]
    
=======
    def g(x):
        return x - 1
    def f(x):
        while x:
            x = g(x)
    import cProfile
    import time
    t1 = time.time()
    cProfile.run("f(10000000)")
    t2 = time.time()
    f(10000000)
    t3 = time.time()
    print t2 - t1, t3 - t2, (t3 - t2) / (t2 - t1)
>>>>>>> other
except Exception, e:
    print "Exception: ", type(e)
    print e

