#!/bin/env python

import sys
import py
from pypy.rpython.rarithmetic import r_int, r_uint, r_ulonglong, r_longlong
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



def bar(x, y):
    return x and (not y)

f = compile_function(bar, [r_uint, r_uint])

try:
    check(f, bar, r_uint(sys.maxint+1), r_uint(42))
    check(f, bar, 4, 5)    
except py.test.Item.Skipped:
    print 'Test skipped'


#compile_function(s.is_perfect_number, [int])
