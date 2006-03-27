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


def foo(x):
    pass

def xxx():
    pass

def bar(x, y):
    try:
        foo(x)
        z = ovfcheck(x+y)
        xxx()
        return z
    except OverflowError:
        while x:
            x = x-1
        return x
    except IndexError:
        return 52
            

def bar(x, y):
    foo(x)
    foo(None)

f = compile_function(bar, [int, int])

try:
    check(f, bar, r_uint(sys.maxint+1), r_uint(42))
    check(f, bar, 4, 5)    
except py.test.Item.Skipped:
    print 'Test skipped'


#compile_function(s.is_perfect_number, [int])
