import turbogears
from turbogears import controllers
import cherrypy

import autopath

from pypy.translator.js.test.runtest import compile_function
from pypy.translator.js.modules import dom,xmlhttp

import thread
import os

def move_it():
    pass

def js_fun():
    document = dom.get_document()
    obj = document.createElement('img')
    obj.id = 'gfx'
    obj.setAttribute('style', 'position:absolute; top:0; left:0;')
    obj.src = '/static/gfx/BubBob.gif'
    document.body.appendChild(obj)

def esc_html(data):
    return data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") \
           .replace("\n", "<br/>").replace(" ", "&nbsp;")
    
class Root(controllers.Root):
    def __init__(self):
        self.lock = thread.allocate_lock()
        self.lock.acquire()
        self.results = None

    @turbogears.expose(html="jsdemo.templates.main")
    def index(self):
        import time
        return dict(now=time.ctime(), onload=self.jsname, code=self.jssource)
    
    @turbogears.expose(format="json")
    def send_result(self, result, exc):
        self.results = (result, exc)
        self.lock.release()
        return dict()
    
    def get_some_info(self, *args, **kwargs):
        print "Info: %s" % cherrypy.response.body.read()
        return dict()
    
    get_some_info.exposed = True
    
    def js_basic_js(self):
        def gen(data):
            yield data
        
        cherrypy.response.headerMap['Content-Type'] = 'test/javascript'
        cherrypy.response.headerMap['Content-Length'] = len(self.jssource)
        return gen(self.jssource)
    
    def wait_for_results(self):
        self.lock.acquire()
        self.lock.release()
    
    js_basic_js.exposed = True
