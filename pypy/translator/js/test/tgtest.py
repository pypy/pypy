
""" TurboGears browser testing utility
"""

import thread

import pkg_resources
pkg_resources.require("TurboGears")

import cherrypy
import os
import sys
import webbrowser

from pypy.jsdemo.jsdemo import controllers

conf_file = os.path.join(os.path.dirname(controllers.__file__), "..", "dev.cfg")

class run_tgtest(object):
    def __init__(self, compiled_fun, tg_root = None):
        def cont():
            cherrypy.server.wait()
            webbrowser.open("http://localhost:8080/")
            cherrypy.root.wait_for_results()
            self.results = cherrypy.root.results
            cherrypy.server.stop()
            cherrypy.server.interrupt = SystemExit()
        
        cherrypy.config.update(file=conf_file)

        if tg_root is None:
            cherrypy.root = controllers.Root()
        else:
            cherrypy.root = tg_root()
        cherrypy.root.jssource = compiled_fun.js.tmpfile.open().read()
        cherrypy.root.jsname = compiled_fun.js.translator.graphs[0].name
        
        thread.start_new_thread(cont, ())
        sys.path.insert(1, os.path.join(os.path.dirname(controllers.__file__), ".."))
        cherrypy.server.start()
