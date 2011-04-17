
try:
    try:
        import pypyjit
        pypyjit.set_param(threshold=3, inlining=True)
    except ImportError:
        pass
    class A(object):
        x = 1
        y = 2
    def sqrt(y):
        a = A()
        for i in range(y):
            assert a.y == 2
            assert A.__dict__['x'] == i + 1
            A.x += 1
        return a.x

    print sqrt(1000000)

except Exception, e:
    print "Exception: ", type(e)
    print e

