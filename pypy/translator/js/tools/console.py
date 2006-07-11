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
#def onchange_callback(data):
#    get_document().getElementById("text").value = data['data']
##
##def command_run(data):
##    #logDebug(data['retval'])
##    #logDebug(data['data'])
##    for i in data['retval'].split("\n"):
##        #logDebug(i)
##        console.add_line(i)
##    if data['source']:
##        jseval(data['source'] + "\nf()")
##        #console.add_line(data['retval'].replace("\n", "<br>"))
##    console.go = False
##    console.add_line(">>> ")
##
##class Console(object):
##    def __init__(self):
##        self.to_run = ""
##        self.shift = False
##        self.go = False
##    
##    def add_line(self, text):
##        self.data_field.innerHTML += "<br>" + text
##    
##    def onload(self, df):
##        self.data_field = df
##        df.innerHTML = ""
##        self.add_line("This is some console")
##        self.add_line(">>> ")
##    
##    def history_up(self):
##        pass
##    
##    def history_down(self):
##        pass
##    
##    def backspace(self):
##        # FIXME: terribly inneficient
##        #if self.data_field.innerHTML.endswith("&nbsp;"):
##        #    self.data_field.innerHTML = self.data_field.innerHTML[:-5]
##        # seems to be pypy bug, so you cannot delete spaces
##        #else:
##        self.data_field.innerHTML = self.data_field.innerHTML[:-1]
##        self.to_run = self.to_run[:-1]
##    
##    def run(self):
##        if self.go:
##            self.add_line(">>> ")
##            ConsoleRootInstance.run_command(self.to_run, command_run)
##            self.to_run = ""
##        else:
##            self.add_line("... ")
##            self.to_run += "<br>"
##            self.go = True
##    
##    def add_space(self):
##        self.data_field.innerHTML += "&nbsp;"
##        self.to_run += " "
##        self.go = False
##    
##    def add_key(self, char):
##        #if self.shift:
##        #    char = chr(kc)
##        #else:
##        #    char = chr(kc + 32)
##        self.data_field.innerHTML += char
##        self.to_run += char
##        self.go = False
##    
##    def shift_up(self):
##        self.shift = False
##    
##    def shift_down(self):
##        self.shift = True

##console = Console()
##
##def onchange(key):
##    kc = key.keyCode
##    if kc == 38: # up key
##        console.history_up()
##    elif kc == 40: # down key
##        console.history_down()
##    elif kc == 13: # return
##        console.run()
##    elif kc == 8: # backspace
##        console.backspace()
##    elif chr(key.charCode) == " ":
##        console.add_space()
##    else:
##        console.add_key(chr(key.charCode))
##    logDebug(chr(key.charCode))
##    log(str(key.keyCode))
##    #data_field = get_document().getElementById("data")
##    #data_field.innerHTML = chr(key.keyCode)
##    #logDebug(str(conn.childNodes[1].value))
##    #ConsoleRootInstance.run_command(data_field.innerHTML, comeback)

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
