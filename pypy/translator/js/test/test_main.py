
""" tests of rpython2javascript function
"""

from pypy.translator.js.main import rpython2javascript
from pypy.translator.js import conftest
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, described
import py
import sys

#if not conftest.option.browser:
#    py.test.skip("Works only in browser (right now?)")

class A(BasicExternal):
    def method(a={'a':'a'}):
        pass
    method = described(retval={'a':'a'})(method)

a = A()

def fun(x='3'):
    return a.method({'a':x})['a']

def fff():
    pass

def test_bookkeeper_cleanup():
    assert rpython2javascript(sys.modules[__name__], ["fun"])
    assert rpython2javascript(sys.modules[__name__], ["fun"])

def test_module_none():
    assert rpython2javascript(None, "fff")
