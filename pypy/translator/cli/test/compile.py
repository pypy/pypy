#!/bin/env python

import py
from pypy.translator.cli import conftest
from pypy.translator.cli.test.runtest import compile_function

py.test.Config.parse(py.std.sys.argv[1:])

#conftest.option.view = True
conftest.option.source = True
conftest.option.wd = True
conftest.option.nostop = True
conftest.option.stdout = True

def bar(x, y):
    return x/y


f = compile_function(bar, [int, int])
