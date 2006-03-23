#!/bin/env python

import py
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
    if x>y:
        return x
    else:
        return y



f = compile_function(bar, [int, int])

check(f, bar, 3, 3)
check(f, bar, 4, 5)

#compile_function(s.is_perfect_number, [int])
