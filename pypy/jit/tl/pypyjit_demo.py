
def f0():
    print "simple loop"

    i = 0
    while i < 100:
        i = i + 3
    print i
    assert i == 102

def f1():
    print "simple loop with inplace_add"

    i = 0
    while i < 100:
        i += 3
    print i
    assert i == 102

def f():
    print "range object, but outside the loop"

    s = 0
    for i in range(100):
        # XXX implement inplace_add method for ints
        s = s + i
    print s
    assert s == 4950

f()
