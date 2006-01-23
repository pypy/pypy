from __future__ import division
import py

from pypy.translator.js.test.runtest import compile_function
from pypy.rpython.rjs import jseval

def test_jseval1():
    def jseval1(s):
        return jseval(s)
    jseval1_fn = compile_function(jseval1, [str])
    e = "4+7"
    assert jseval1_fn(e) == eval(e)
