#!/bin/env python
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

class Derived(Base):
    def __init__(self, x):
        Base.__init__(self, x)

def foo(x):
    return x+1

def bar(x, y):
    a = Derived(x)
    return a.x


f = compile_function(bar, [int, int])

try:
    pass
except py.test.Item.Skipped:
    print 'Test skipped'

