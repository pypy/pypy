
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
    while i < 1000:
        t = t[1], t[2], t[0]
        i += 1

def f6():
    print     "Arbitrary test function."
    n = 5
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


f5()
