
try:
    for i in xrange(1000):
        "%d %d" % (i, i)

except Exception, e:
    print "Exception: ", type(e)
    print e

