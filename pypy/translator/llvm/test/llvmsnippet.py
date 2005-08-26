from __future__ import division

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

def default_arguments(i1, i2=2, s1="asdf"):
    return i1 + i2 + len(s1)

def call_default_arguments(i, j):
    if j == 0:
        return default_arguments(i)
    elif j == 1:
        return default_arguments(i, 42)
    return default_arguments(i, j, "qwertyuiop")

def list_default_argument(i1, l1=[0]):
    l1.append(i1)
    return len(l1) + l1[-2]

def call_list_default_argument(i1):
    return list_default_argument(i1)

def return_none():
    pass

def shiftleft(i, j):
    return i << j

def shiftright(i, j):
    return i >> j


#float snippets

def float_f1(x):
    return x + 1.2

def float_int_bool(x):
    return x * (2 + True)

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

def array_pop(i):
    a = [0, 1, 2, 3]
    return a.pop() + len(a) + a[i]

def newlist_zero_arg(i):
    a = []
    a.append(i)
    return len(a) + a[0]

def big_array(i):
    return [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17][i]

glob_array = [[i] * 5 for i in range(5)]

def access_global_array(x, y, z):
    result = glob_array[x][y]
    glob_array[x][y] = z
    return result

def circular_list(n):
    lst = []
    i = 0
    while i < n:
        i += 1
        lst = [lst]
    return len(lst)


#class snippets

class A(object):
    def __init__(self):
        self.a = 14
        self.b = False

def class_simple():
    a = A()
    return a.a

class B(A):
    def __init__(self):
        self.a = 14
        self.b = False
 
    def change(self, newa):
        self.a = newa * 5

def class_simple1(newa):
    b = B()
    b.change(newa)
    return b.a

class C(A):
    def __init__(self, a):
        self.a = a
        self.b = 1

def class_simple2(newa):
    b = B()
    b.change(newa)
    c = C(b)
    return c.a.a

class AA(object):
    x = 8
    def __init__(self):
        self.a = 15
        self.b = 16
    def g(self):
        return self.a + self.b

class BB(AA):
    x = 3
    def g(self):
        return self.a + self.a
    
def class_inherit1():
    aa = AA()
    bb = BB()
    return aa.x + bb.x
    
def class_inherit2():
    aa = AA()
    bb = BB()
    return aa.g() - bb.g() 

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

class GGG(object):
    pass

ggg = GGG()
ggg.a = 36
ggg.b = (1, 2, 3)
ggg.c = [1, 2, 3]

def global_instance(x):
    previous = ggg.a
    previous1 = ggg.c[-1]
    ggg.c.append(x)
    d = ggg.b[1]
    ggg.a = x
    36 + d + 3
    return previous + d + previous1

class FFF: pass
fff = FFF()
fff.x = 10

def getset(x):
    res = fff.x
    fff.x = x
    return res

def testgetset(y):
    res1 = getset(y)
    res2 = getset(y)
    return res1 + res2

def degrading_func(obj):
    if isinstance(obj, C):
        return obj.a + obj.b
    elif isinstance(obj, B):
        return obj.a
    return -90

def call_degrading_func(flag):
    if flag:
        return degrading_func(C(-37))
    else:
        return degrading_func(B())

circular_instance = GGG()
circular_instance.x = circular_instance
circular_instance.b = 10

def circular_classdef():
    return circular_instance.x.x.x.x.x.x.x.b


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

class CCC(BBB):
    def __init__(self):
        AAA.__init__(self)
        BBB.__init__(self)

    def cmethod(self):
        return 13

def attribute_from_base_class():
    a = AAA()
    b = BBB()
    return a.a + b.a + b.b

def method_of_base_class():
    a = AAA()
    b = BBB()
    return a.get() + AAA.get(b) + b.get() + b.g()

def direct_call_of_virtual_method():
    a = AAA()
    b = BBB()
    c = CCC()
    return a.get() + b.get() + c.get()

def ifisinstance(a):
    if isinstance(a, CCC):
        return a.cmethod()
    elif isinstance(a, BBB):
        return a.b
    return 1

def flow_type():
    a = AAA()
    b = BBB()
    c = CCC()
    return ifisinstance(a) + ifisinstance(b) + ifisinstance(c)

class CLA(object):
    def __init__(self):
        self.a = 1

class CLB(CLA):
    def __init__(self):
        self.a = 2
        self.b = 1

def merge_classes(flag):
    if flag:
        a = CLA()
    else:
        a = CLB()
    return a.a

class CLC(object):
    def __init__(self, a):
        self.a = a

def attribute_instance(x):
    if x:
        a = CLC(CLA())
    else:
        a = CLC(CLB())
    return a.a.a


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

def constant_tuple(i):
    return len((1, 2, "asdf")) + i


#PBC snippets

class PBCClass(object):
    def __init__(self, a):
        self.a = a
        self.b = 12

    def _freeze_(self):
        return True

    def get(self, i):
        return self.a[i]

pbc = PBCClass([1, 2, 3, 4])

def pbc_passing(pbc, i):
    return pbc.a[i] + pbc.get(i)

def pbc_function1(i):
    return pbc_passing(pbc, i)


class CIRCULAR1(object):
    def __init__(self):
        self.a = [1, 2, 3, 4]
        self.pbc = pbc1

    def get(self, i):
        return self.a[i] + self.pbc.a.a[i] + self.pbc.b

class CIRCULAR2(CIRCULAR1):
    def __init__(self):
        pass

pbc1 = PBCClass(CIRCULAR2())
pbc1.a.pbc = pbc1
pbc1.a.a = range(4)

def pbc_function2(i):
    a = CIRCULAR1()
    return a.get(i)
