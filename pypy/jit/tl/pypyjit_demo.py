TESTNAME = 'test_builtin'


def do():
    __import__('test.' + TESTNAME)
    print "---ending 1---"

class A(object):
    def __init__(self, x):
        self.x = x
        self.y = x
        self.count = 0

    def increment(self):
        self.count += 1
        count = self.count
        self.reset(self.count)
        self.count += count
    
    def reset(self, howmuch):
        for i in range(howmuch):
            self.count -= 1

    def f(self):
        self.increment()
        return self.x + self.y + 1

def simple_loop():
    print "simple loop"
    import time
    global a
    a = A(10)
    a = A(10)
    a = A(10)
    a = A(10)
    a = A(10)
    a = A(1)
    print a
    print a
    i = 0L
    N = 1000L
    N = 10000000L
    step = 3
    start = time.clock()
    odd = 0
    while i < N:
        i = i + 1
    end = time.clock()
    print i
    print end-start, 'seconds'

def g(i):
    for k in range(i, i +2):
        pass

def loop():
    for i in range(10000):
        g(i)


class B(object):
    def foo(self, n):
        return n+1


def method(n):
    obj = B()
    i = 0
    while i<n:
        i = obj.foo(i)
    return i


def add(a, b):
    return a+b

def funccall(n):
    i = 0
    while i<n:
        i = add(i, 1)
    return i


try:
    #do()
    #loop()
    #simple_loop()
    method(100)
    #funccall(100)
    print "---ending 2---"
except BaseException, e:
    print "---ending 0---"
    print '/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\'
    import sys
    import traceback
    traceback.print_exception(*sys.exc_info())
