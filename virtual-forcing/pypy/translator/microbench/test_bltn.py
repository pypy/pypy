N = int(2**19 - 1)

#
def test_call_sin():
    from math import sin
    
    x = 1.0
    c = 0
    n = N
    while c < n:
        x = sin(x)
        c += 1

def test_call_fabs():
    from math import fabs
    
    x = -1.0
    c = 0
    n = N
    while c < n:
        x = fabs(x)
        c += 1

class foo(object):
    pass

class bar(foo):
    pass

class baz(bar):
    pass

def test_isinstance1():
    f = foo()
    b1 = bar()
    b2 = baz()
    for x in xrange(100000):
        isinstance(b1, foo)
        isinstance(b1, baz)
        isinstance(f, bar)
        isinstance(b2, foo)

def test_isinstance2():
    for x in xrange(100000):
        isinstance(1, float)
        isinstance(1, int)
        isinstance("foo", basestring)

def test_isinstance3():
    b2 = baz()
    for x in xrange(100000):
        isinstance(b2, (bar, baz))
        isinstance(b2, (bar, baz))
        isinstance(b2, (bar, baz))
        isinstance(b2, (bar, baz))
        isinstance(b2, (bar, baz))

# old-style

class Foo:
    pass

class Bar(Foo):
    pass

class Baz(Bar):
    pass

def test_isinstance1_old_style():
    f = Foo()
    b1 = Bar()
    b2 = Baz()
    for x in xrange(100000):
        isinstance(b1, Foo)
        isinstance(b1, Baz)
        isinstance(f, Bar)
        isinstance(b2, Foo)

def test_isinstance3_old_style():
    b2 = Baz()
    for x in xrange(100000):
        isinstance(b2, (Bar, Baz))
        isinstance(b2, (Bar, Baz))
        isinstance(b2, (Bar, Baz))
        isinstance(b2, (Bar, Baz))
        isinstance(b2, (Bar, Baz))

