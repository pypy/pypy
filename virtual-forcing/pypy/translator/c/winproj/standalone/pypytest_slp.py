from stackless import *

c1 = coroutine()
c2 = coroutine()

def f(name, n, other):
    print "starting", name, n
    for i in xrange(n):
        print name, i, "switching to", other
        other.switch()
        print name, i, "back from", other
    return name

c1.bind(f, "eins", 10, c2)
c2.bind(f, "zwei", 10, c1)

c1.switch()
