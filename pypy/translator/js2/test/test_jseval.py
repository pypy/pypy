from __future__ import division
import py

from pypy.translator.js2.test.runtest import compile_function
from pypy.rpython.lltypesystem import lltype 
from pypy.rpython.rjs import jseval
from pypy.translator.js2 import conftest

def jsnative(cmd):
    def do():
        return jseval(cmd)
    return do

getDate = jsnative("new Date().getDate()")
getTime = jsnative("Math.floor(new Date().getTime())")

#
def test_jseval1():
    def jseval1(s):
        return jseval(s)

    jseval1_fn = compile_function(jseval1, [str])
    e = "4+7"
    assert jseval1_fn(e) == eval(e)

def test_jsnative1():
    from time import localtime

    def jsnative1():
        getTime()
        return getDate()

    jsnative1_fn = compile_function(jsnative1, [])
    assert jsnative1_fn() == localtime()[2]

callbacks = []
#n_times_called = lltype.malloc(lltype.GcArray(lltype.Signed), 1) 
n_times_called = [0]

def callback_function():
    n_times_called[0] += 1
    jseval("document.title=" + str(n_times_called[0]))
    jseval("setTimeout('callback_function()', 100)")

def test_register_callback():
    py.test.skip("Hangs")
    if not conftest.option.browser:
        py.test.skip("works only in a browser (use py.test --browser)")

    def register_callback():
        callback_function() #..start timer
        start_time = current_time = int(getTime())
        while current_time - start_time < 1000:
            current_time = int(getTime())
        return n_times_called[0]

    register_callback_fn = compile_function(register_callback, [])
    result = register_callback_fn()
    assert result == 1
