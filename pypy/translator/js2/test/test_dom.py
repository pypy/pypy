
""" test of DOM related functions
"""

import py

from pypy.translator.js2.test.runtest import compile_function
from pypy.translator.js2.modules.dom import document, Node, get_document, setTimeout
from pypy.translator.js2 import conftest

import time

if not conftest.option.browser:
    py.test.skip("Works only in browser (right now?)")

def test_document_base():
    def f():
        return get_document().getElementById("dupa")
        #document.getElementById("dupa").setInnerHTML("<h1>Fire!</h1>")
        #return document.getElementById("dupa")
    
    fn = compile_function(f, [], html = 'html/test.html')
    assert fn() == '[object HTMLHeadingElement]'

class Mover(object):
    def __init__(self, elem):
        self.x = 0
        self.y = 0
        self.dir = 1
        self.elem = elem#get_document().getElementById(elem)
    
    def move_it_by(self, obj, dx, dy):
        if self.dir < 0:
            dx = -dx
            dy = -dy
        self.x += dx
        self.y += dy
        if self.x > 100:
            self.dir = -1
        if self.x < 0:
            self.dir = 1
        obj.style.left = str(int(obj.style.left) + dx) + "px"
        obj.style.top = str(int(obj.style.top) + dy) + "px"

    def move_it(self):
        #self.move_it_by(self.elem, 3, 3)
        self.move_it_by(get_document().getElementById(self.elem), 3, 3)

movers = [Mover("anim_img"), Mover("anim_img2")]
movers[1].x = 20

def move_it():
    movers[0].move_it()
    movers[1].move_it()

def test_anim_f():  
    def anim_fun():
        obj = get_document().getElementById("anim_img")
        obj.setAttribute('style', 'position: absolute; top: 0; left: 0;')
        obj2 = get_document().getElementById("anim_img2")
        obj2.setAttribute('style', 'position: absolute; top: 50; left: 0;')
        move_it()
        return get_document().getElementById("anim_img").style.left
    
    fn = compile_function(anim_fun, [], html = 'html/anim.html')
    assert fn() == '3px'
