from __future__ import division
import py

from pypy.translator.js.test.runtest import compile_function
from pypy.rpython.lltypesystem import lltype 
from pypy.rpython.rjs import jseval
from pypy.translator.js import conftest

py.test.skip("WIP")

def test_bugme():
    def bugme(i):
        if i >= 0:
            return i
        else:
           return [1,2,3]
    bugme_fn = compile_function(bugme, [int])
    assert bugme_fn(-1) == bugme(-1)
    assert bugme_fn(1) == bugme(1)
