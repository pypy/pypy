import autopath

#function snippets
def simple1():
    return 1

def simple2():
    return False

def simple3(i):
    c = "Hello, Stars!"
    return c[i]

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

def array_len():
    a = [1] * 10
    return len(a)

def array_append(i):
    a = [0] * 3
    a.append(10)
    return a[i]

def array_reverse(i):
    a = [0] * 2
    a[1] = 1
    a.reverse()
    return a[i]

def rangetest(i):
    return range(10)[i]

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

#simple inheritance snippets
class AAA(object):
    def __init__(self):
        self.a = 1

    def get(self):
        return 4

    def g(self):
        return self.a

class BBB(AAA):
    def __init__(self):
        AAA.__init__(self)
        self.b = 2

    def get(self):
        return 5

def attribute_from_base_class():
    a = AAA()
    b = BBB()
    return a.a + b.a + b.b

def method_of_base_class():
    a = AAA()
    b = BBB()
    return a.get() + AAA.get(b) + b.get() + b.g()


#string snippets
def string_f1(i):
    j = 0
    ret = ""
    while j < i:
         ret += "abc"
         j += 1
    return ret

def string_f2(i, j):
    return string_f1(i)[j]


#tuple snippets
def tuple_f1(i):
    return (1, "asdf", i)[2]

def tuple_f2(i):
    return (i, "test", "another one", [1, 2, 3])

def tuple_f3(i):
    j, s1, s2, l = tuple_f2(i)
    return j
