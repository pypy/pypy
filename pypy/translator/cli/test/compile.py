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

class Base:
    def __init__(self, x):
        self.x = x

    def compute(self):
        return self.x

class Derived(Base):
    def __init__(self, x):
        Base.__init__(self, x+42)

def foo(cls, x):
    return cls(x).compute()

def bar(x, y):
    b = Derived(x)
    return foo(Base, x) + foo(Derived, y)

f = compile_function(bar, [int, int])

try:
    check(bar, f, 42, 13)
except py.test.Item.Skipped:
    print 'Test skipped'

