from __future__ import division
import py

from pypy.translator.js.test.runtest import compile_function
from pypy.rpython.lltypesystem import lltype 
from pypy.rpython.rjs import jseval
from pypy.translator.js import conftest

class jsnative(object):
    def __init__(self, cmd):
        self._cmd = cmd

    def __call__(self):
        return jseval(self._cmd)

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
        return jseval("new Date().getDate()")
        #return getDate()

    jsnative1_fn = compile_function(jsnative1, [])
    assert jsnative1_fn() == localtime()[2]

callbacks = []
n_times_called = lltype.malloc(lltype.GcArray(lltype.Signed), 1) 

def callback_function():
    n_times_called[0] += 1
    jseval("setTimeout('callback_function()', 10)")

#def add_callback_function(translator):
#    a  = translator.annotator
#    bk = a.bookkeeper
#    s_cb = bk.immutablevalue(callback_function)
#    bk.emulate_pbc_call('callback_function', s_cb, [])
#    a.complete()
#    translator.rtyper.specialize_more_blocks()  
    
def test_register_callback():
    if not conftest.option.jsbrowser:
        py.test.skip("works only in a browser (use py.test --browser)")

    def register_callback():
        callback_function()
        #callbacks.append(callback_function)
        #jseval("setTimeout('callback_function()', 10)")
        start_time = current_time = int(jseval("Math.floor(new Date().getTime())"))
        while current_time - start_time < 1000:
            current_time = int(jseval("Math.floor(new Date().getTime())"))
        return n_times_called

    register_callback_fn = compile_function(register_callback, [])
    result = register_callback_fn()
    print 'result=%d' % result
    assert result > 1
