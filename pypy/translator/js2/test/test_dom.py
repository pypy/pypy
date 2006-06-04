
""" test of DOM related functions
"""

import py

from pypy.translator.js2.test.runtest import compile_function
from pypy.translator.js2.modules.dom import get_document
from pypy.translator.js2 import conftest

import time

if not conftest.option.browser:
    py.test.skip("Works only in browser (right now?)")

class TestDOM(object):
    def test_document_base(self):
        def f():
            get_document().getElementById("dupa").setInnerHTML("<h1>Fire!</h1>")
            return get_document().getElementById("dupa")
        
        fn = compile_function(f, [], html = 'html/test.html')
        assert fn() == '[object HTMLHeadingElement]'
