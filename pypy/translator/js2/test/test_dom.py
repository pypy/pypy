
""" test of DOM related functions
"""

import py

from pypy.translator.js2.test.runtest import compile_function
from pypy.translator.js2.modules.dom import document, setTimeout, Node
from pypy.translator.js2 import conftest

import time

if not conftest.option.browser:
    py.test.skip("Works only in browser (right now?)")

class TestDOM(object):
    def test_document_base(self):
        def f():
            return document.getElementById("dupa")
            #document.getElementById("dupa").setInnerHTML("<h1>Fire!</h1>")
            #return document.getElementById("dupa")
        
        fn = compile_function(f, [], html = 'html/test.html')
        assert fn() == '[object HTMLHeadingElement]'

    def test_anim(self):
        def move_it_by(obj, dx, dy, dir):
            if dir < 0:
                dx = -dx
                dy = -dy
            obj.getStyle().setLeft(str(int(obj.getStyle().getLeft()) + dx) + "px")
            obj.getStyle().setTop(str(int(obj.getStyle().getTop()) + dy) + "px")
        
        def move_it():
            move_it_by(get_document().getElementById("anim_img"), 3, 3, 1)
            setTimeout('move_it()', 100)
        
        def anim_fun():
            obj = get_document().getElementById("anim_img")
            obj.setAttribute('style', 'position: absolute; top: 0; left: 0;')
            setTimeout('move_it()', 100)
            move_it()
        
        fn = compile_function(anim_fun, [], html = 'html/anim.html', is_interactive = True)
        assert fn() == 'ok'
