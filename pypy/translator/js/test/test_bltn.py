""" blttest - some tests of builtin stuff
"""

import py

from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc
from pypy.translator.js.test.runtest import compile_function, check_source_contains

# check rendering dom.document
def test_simple_builtin():
    from pypy.translator.js.modules.dom import document
    def test_document_call():
        return document.getElementById("some_id")
    
    fn = compile_function(test_document_call, [])
    assert check_source_contains(fn, "= document")
    assert check_source_contains(fn, "\.getElementById")

# check rendering transparent proxy
class SomeProxy(BasicExternal):
    _render_xmlhttp = True
    
    _methods = {
        'some_method' : MethodDesc([], 3),
    }
    
class SomeNode(BasicExternal):
    _fields = {
        'some_callback' : MethodDesc([3], 3),
    }

SomeProxyInstance = SomeProxy()

def test_simple_proxy():
    def simple_proxy():
        retval = SomeProxyInstance.some_method()
    
    fn = compile_function(simple_proxy, [])
    assert check_source_contains(fn, "loadJSONDoc\('some_method'")

SomeNodeInstance = SomeNode()
SomeNodeInstance._render_name = 's'

# next will try out the callback
def test_callback():
    def callback(a):
        return a
    
    def callback_stuff():
        SomeNodeInstance.some_callback = callback
    
    fn = compile_function(callback_stuff, [])
    assert check_source_contains(fn, "\.some_callback = callback")

def test_get_elements():
    from pypy.translator.js.modules import dom
    
    def getaa(tname):
        return dom.document.getElementsByTagName(tname)[0].nodeValue
    
    def some_stuff():
        one = getaa("some")
        if one:
            two = getaa("other")
            return two
        #    if two:
        #        return one + two
        #    else:
        #        return one
        return one
    
    fn = compile_function(some_stuff, [])
