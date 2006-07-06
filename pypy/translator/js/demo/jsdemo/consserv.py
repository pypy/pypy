
""" nb-server - server side of multiuser notebook
"""

import turbogears
import cherrypy
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc
from pypy.translator.js.demo.jsdemo.controllers import Root
from cherrypy import session

import re, time, sys, os, urllib, socket, copy

from pypy.translator.js.test.runtest import compile_function


from pypy.translator.js.modules._dom import Node, get_document, setTimeout, alert
#from pypy.translator.js.modules.xmlhttp import XMLHttpRequest
from pypy.translator.js.modules.mochikit import logDebug, createLoggingPane, log
from pypy.translator.js.modules.bltns import date

class ConsoleRoot(BasicExternal, Root):
    _methods = {
        'run_command' : MethodDesc([('str_to_eval', 'ss'), ('callback', lambda : None)], {'aa':'aa'})
    }
    
    _render_xmlhttp = True
    
    @turbogears.expose(html='jsdemo.templates.console')
    def index(self):
        return dict(now=time.ctime(), onload=self.jsname, code=self.jssource)

    @turbogears.expose(format="json")
    def run_command(self, str_to_eval):
        # we need what has changed
        # we try to run it...
        
        lines = str_to_eval.split("<br>")
        for num, line in enumerate(lines):
            if not line.startswith(" "):
                lines[num] = "    " + line
        all_text = "\n".join(["def f():"] + lines[:-1])
        print all_text
        try:
            exec(all_text)
            fn = compile_function(f, [])
            retval = "compilation ok"
            source = fn.js.tmpfile.open().read()
        except Exception, e:
            print str(e)
            retval = str(e)
            source = ""
        
        return dict(data=all_text, retval=retval, source=source)

ConsoleRootInstance = ConsoleRoot()
