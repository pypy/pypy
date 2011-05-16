
try:
    def f(x):
        i = 0
        while i < x:
            range(i)
            i += 1
    f(10000)
except Exception, e:
    print "Exception: ", type(e)
    print e

