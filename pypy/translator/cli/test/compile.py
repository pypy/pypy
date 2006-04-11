#!/bin/env python
import autopath
import sys
import py
from pypy.rpython.rarithmetic import r_int, r_uint, r_ulonglong, r_longlong, ovfcheck
from pypy.translator.test import snippet as s
from pypy.translator.cli import conftest
from pypy.translator.cli.test.runtest import compile_function

py.test.Config.parse(py.std.sys.argv[1:])

#conftest.option.view = True
#conftest.option.source = True
conftest.option.wd = True
#conftest.option.nostop = True
#conftest.option.stdout = True

def check(f, g, *args):
    x = f(*args)
    y = g(*args)
    if x != y:
        print x, '!=', y
    else:
        print 'OK'


class MyClass:
    INCREMENT = 1

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def compute(self):
        return self.x + self.y

    def compute_and_multiply(self, factor):
        return self.compute() * factor

    def static_meth(x, y):
        return x*y
    static_meth = staticmethod(static_meth)

##    def class_meth(cls, x, y):
##        return x*y + cls.INCREMENT
##    class_meth = classmethod(class_meth)

    def class_attribute(self):
        return self.x + self.INCREMENT

class MyDerivedClass(MyClass):
    INCREMENT = 2

    def __init__(self, x, y):
        MyClass.__init__(self, x+12, y+34)

    def compute(self):
        return self.x - self.y



def init_and_compute(cls, x, y):
    return cls(x, y).compute()


def bar(x, y):
    return init_and_compute(MyClass, x, y) + init_and_compute(MyDerivedClass, x, y)


f = compile_function(bar, [int, int])

try:
    check(bar, f, 42, 13)
except py.test.Item.Skipped:
    print 'Test skipped'

