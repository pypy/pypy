import pypyjit
pypyjit.set_param(threshold=200)


def f(n):
    pairs = [(0.0, 1.0), (2.0, 3.0)] * n
    mag = 0
    for (x1, x2) in pairs:
        dx = x1 - x2
        mag += ((dx * dx ) ** (-1.5))            
    return n

try:
    print f(301)

except Exception, e:
    print "Exception: ", type(e)
    print e

