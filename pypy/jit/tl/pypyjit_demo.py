
try:
    import numpy
    a = numpy.array(range(10))
    b = a + a + a
    print b[3]
    
except Exception, e:
    print "Exception: ", type(e)
    print e

