import autopath

#function snippets
def simple1():
    return 1

def simple2():
    return False

def simple3():
    c = "Hello, Stars!"
    return c

def simple4():
    return 3 + simple1()

def simple5(b):
    if b:
        x = 12
    else:
        x = 13
    return x

def simple6():
    simple4()
    return 1

def ackermann(n, m):
    if n == 0:
        return m + 1
    if m == 0:
        return ackermann(n - 1, 1)
    return ackermann(n - 1, ackermann(n, m - 1))

def calling1(m):
    if m > 1:
        return calling2(m - 1)
    return m

def calling2(m):
    if m > 1:
        return calling1(m - 1)
    return m

#array snippets

def array_simple():
    a = [42]
    return a[0]

def array_simple1(item):
    a = [item] * 10
    i = 0
    v = 0
    while i < 10:
        v += a[i]
        i += 1
    return v

def array_setitem(i):
    a = [1] * 10
    a[i] = i
    a[1] = 12
    a[2] = 13
    return a[i]

def array_add(a0, a1, b0, b1, i):
    a = [0] * 2
    b = [0] * 2
    a[0] = a0
    a[1] = a1
    b[0] = b0
    b[1] = b1
    return (a + b)[i]

def double_array():
    a = [15]
    b = [a]
    return b[0][0]

def double_array_set():
    a = [15] * 3
    b = [a] * 3
    b[0][0] = 1
    return b[1][0]

def bool_array():
    a = [False] * 100
    a[12] = True
    return a[12]

def callee(array):
    return array[0]

def array_arg(i):
    a = [i - 5] * 12
    return callee(a)

#class snippets

class A(object):
    def __init__(self):
        self.a = 14
        self.b = False

def class_simple():
    a = A()
    return a.a

class B(object):
    def __init__(self):
        self.a = 14
        self.b = False
 
    def change(self, newa):
        self.a = newa * 5

def class_simple1(newa):
    b = B()
    b.change(newa)
    return b.a

class C(object):
    def __init__(self, a):
        self.a = a
        self.b = 1

def class_simple2(newa):
    b = B()
    b.change(newa)
    c = C(b)
    return c.a.a

class D(object):
    def __init__(self, a, length):
        self.a = [a] * length
        self.length = length

    def set_range(self):
        i = 0
        while i < self.length:
            self.a[i] = i
            i += 1

def id_int(i):
    d = D(1, i + 1)
    d.set_range()
    return d.a[i]
