import pypyjit
pypyjit.set_param(threshold=200)


def g(*args):
    return len(args)

def f(n):
    s = 0
    for i in range(n):
        l = [i, n, 2]
        s += g(*l)
    return s

try:
    print f(301)

except Exception, e:
    print "Exception: ", type(e)
    print e

