#!/usr/bin/env python
""" some console
"""

import autopath

import py

from pypy.translator.js import conftest

conftest.option.tg = True
conftest.option.browser = "default"

from pypy.translator.js.test.runtest import compile_function
from pypy.translator.js.modules._dom import Node, get_document, setTimeout, alert
#from pypy.translator.js.modules.xmlhttp import XMLHttpRequest
from pypy.translator.js.modules.mochikit import logDebug, createLoggingPane, log
from pypy.translator.js.modules.bltns import date

from pypy.translator.js.demo.jsdemo.consserv import ConsoleRootInstance, ConsoleRoot
from pypy.rpython.rjs import jseval

class Console(object):
    def __init__(self):
        self.data = ""
        self.indent_level = 0
    
    def initialise(self):
        self.elem = get_document().getElementById("data")
    
    def add_data(self, data):
        if self.indent_level == 0 and data == "":
            logDebug(self.data)
            ConsoleRootInstance.run_command(self.data, comeback)
        elif data == "":
            self.indent_level -= 1
        else:
            self.elem.innerHTML += data + "<br/>"
            self.data += data + "\n"
        retval = ""
        for i in range(self.indent_level):
            retval += "  "
        return retval

console = Console()

def comeback(msg):
    pass

def onchange(key):
    kc = key.keyCode
    if kc == ord("\r"):
        inp_elem = get_document().getElementById("inp")
        inp_elem.value = console.add_data(inp_elem.value)

def test_run_console():
    def some_fun():
        #cons = get_document().getElementById("data")
        #write_start(cons)
        createLoggingPane(True)
        console.initialise()
        #data_field = get_document().getElementById("data")
        #console.onload(data_field)
        get_document().onkeypress = onchange
        #get_document().onkeyup = onchangedown
    
    fn = compile_function(some_fun, [], root = ConsoleRoot, run_browser = True)
    fn()

if __name__ == '__main__':
    test_run_console()
