""" blttest
"""

import py

#from pypy.rpython.ootypesystem.bltregistry import BasicExternal
from pypy.translator.js.test.runtest import compile_function

from pypy.rpython.ootypesystem.ootype import Signed, Void, Float, List, String

py.test.skip("External object support not implemented yet")

class Sth(BasicExternal):
    # Take care!
    # we do not annotate it, so we must take care of what we're talking with
    _fields = {
        'a' : Signed,
        'b' : String,
    }
    
    _methods = {
    }

def test_simple():
    def test_new():
        s = Sth()
        s.a = 3
        return s
    
    fn = compile_function(test_new, [])
    fn()
