#!/usr/bin/env python
""" bub-n-bros testing utility
"""

import autopath

import py

from pypy.translator.js import conftest

conftest.option.tg = True
conftest.option.browser = "default"

from pypy.translator.js.test.runtest import compile_function
from pypy.translator.js.modules.dom import Node, get_document, setTimeout, alert
from pypy.translator.js.modules.xmlhttp import XMLHttpRequest
from pypy.translator.js.modules.mochikit import logDebug, createLoggingPane
from pypy.translator.js.modules.dom import get_document

import time
import os

os.chdir("../demo/jsdemo")

#if not conftest.option.browser:
#    py.test.skip("Works only in browser (right now?)")

from pypy.translator.js.demo.jsdemo.bnb import BnbRootInstance

##def msg_dispatcher(data):
##    for i in data['messages']:
##        logDebug(i['type'])
##    BnbRootInstance.get_message(msg_dispatcher)
##
##def test_mochikit():
##    def mochikit():
##        createLoggingPane(True)
##        BnbRootInstance.get_message(msg_dispatcher)
##
##    from pypy.translator.js.proxy.testme.controllers import Root
##    fn = compile_function(mochikit, [], root = Root)
##    fn()

class SpriteContainer(object):
    """ Class containing all sprites
    """
    def __init__(self):
        self.sprite_queues = {}
        self.used = {}
        self.filenames = {}
        self.icon_codes = []
    
    def add_icon(self, icon_code, filename):
        self.filenames[icon_code] = filename
        self.sprite_queues[icon_code] = []
        self.used[icon_code] = []
        # FIXME: Need to write down DictIterator once...
        self.icon_codes.append(icon_code)
    
    def get_sprite(self, icon_code):
        #logDebug(str(len(self.sprite_queues[icon_code])))
        try:
            elem = self.sprite_queues[icon_code].pop()
            elem.style.visibility = "visible"
            self.used[icon_code].append(elem)
            return elem
        except IndexError:
            img = get_document().createElement("img")
            img.setAttribute("src", self.filenames[icon_code])
            img.setAttribute("style", 'position:absolute; left:0px; top:0px; visibility:visible')
            self.sprite_queues[icon_code].append(img)
            get_document().getElementById("playfield").appendChild(img)
            return img
    
    def revive(self):
        for i in self.icon_codes:
            for j in self.sprite_queues[i]:
                j.style.visibility = "hidden"
            self.sprite_queues[i] = self.sprite_queues[i] + self.used[i]
            self.used[i] = []
        
sc = SpriteContainer();

def process_message(msg):
    if msg['type'] == 'def_playfield':
        bgcolor = '#000000'
        get_document().body.setAttribute('bgcolor', bgcolor)
        div = get_document().createElement("div")
        div.setAttribute("id", "playfield")
        div.setAttribute('width', msg['width'])
        div.setAttribute('height', msg['height'])
        div.setAttribute('style', 'position:absolute; top:0px; left:0px')
        get_document().body.appendChild(div)
    elif msg['type'] == 'def_icon':
##        img = get_document().createElement("img")
##        img.setAttribute("src", msg["filename"])
##        img.setAttribute("style", 'position:absolute; left:0; top:0')
##        img.setAttribute("id", msg["icon_code"])
##        get_document().getElementById("playfield").appendChild(img)
        sc.add_icon(msg['icon_code'], msg['filename'])
    elif msg['type'] == 'sprite':
        #img = get_document().getElementById(msg["icon_code"])
        #logDebug(str(img.left) + " " + str(img.right))
        img = sc.get_sprite(msg['icon_code'])
        img.style.left = msg['x'] + 'px'
        img.style.top = msg['y'] + 'px'
    elif msg['type'] == 'end_frame':
        pass
        sc.revive()

def bnb_dispatcher(msgs):
    BnbRootInstance.get_message(bnb_dispatcher)
    for msg in msgs['messages']:
        process_message(msg)
    
def run_bnb():
    def bnb():
        #get_document().
        createLoggingPane(True)
        BnbRootInstance.get_message(bnb_dispatcher)
    
    from pypy.translator.js.demo.jsdemo.bnb import BnbRoot
    fn = compile_function(bnb, [], root = BnbRoot, run_browser = False)
    fn()

if __name__ == '__main__':
    run_bnb()
