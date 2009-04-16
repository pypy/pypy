def f0():
    print "simple loop"

    i = 0
    while i < 100:
        i = i + 3
    print i
    s
    #assert i == 102

def f1():
    print "simple loop with inplace_add"

    i = 0
    while i < 100:
        i += 3
    print i
    assert i == 102

def f2():
    print "range object, but outside the loop"

    s = 0
    for i in range(100):
        s = s + i
    print s

def f3():
    try:
        i = 100
        while i > 0:
            if i == 10:
                raise IndexError
            i -= 1
    except IndexError:
        pass
    else:
        raise AssertionError

def f4():
    s = 0
    for i in range(100):
        if i % 2:
            s += 1
        else:
            s += 2
    print s

def f5():
    t = (1, 2, 3)
    i = 0
    while i < 100:
        t = t[1], t[2], t[0]
        i += 1
    print t

def f6():
    print     "Arbitrary test function."
    n = 21
    i = 0
    x = 1
    while i<n:
        j = 0   #ZERO
        while j<=i:
            j = j + 1
            x = x + (i&j)
        i = i + 1
    print x
    return x

def f7():
    n = "hello"
    i = 0
    while i < 21:
        i = i + 1
    print n

def f13():
    i = 0
    k = 0
    while i < 20000:
        k += call(i)
        i += 1

def call(i):
    k = 0
    for j in range(i, i + 2):
        if j > i + 2:
            raise Exception("Explode")
        k += 1
    return k

try:
    f13()
    #f1()
except Exception, e:
    print '/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\'
    import sys
    import traceback
    traceback.print_exception(*sys.exc_info())
