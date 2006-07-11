#!/usr/bin/env python
""" very simple example of what we can really achieve
"""

import autopath

from pypy.translator.js.test.runtest import compile_function
from pypy.translator.js.modules._dom import setTimeout, get_document
from pypy.rpython.ootypesystem.bltregistry import MethodDesc, BasicExternal
from pypy.translator.js import commproxy

commproxy.USE_MOCHIKIT = False

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
#from SimpleHTTPServer import SimpleHTTPRequestHandler

HTML_PAGE = """
<html>
<head>
  <title>Example</title>
  <script type="text/javascript" src="jssource"/>
</head>
<body onload="runjs()">
This is a test!<br/>
<div id="counter"></div>
</body>
</html>
"""

httpd = None

def callback(data):
    get_document().getElementById("counter").innerHTML = data['counter']
    runjs()

def runjs():
    httpd.some_callback(callback)

class Server(HTTPServer, BasicExternal):
    # Methods and signatures how they are rendered for JS
    _methods = {
        'some_callback' : MethodDesc([('callback', lambda : None)], {'aa':'aa'})
    }
    
    _render_xmlhttp = True
    
    def __init__(self, *args, **kwargs):
        HTTPServer.__init__(self, *args, **kwargs)
        self.counter = 0

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        if path.endswith("/"):
            path = path[:-1]
        if path.startswith("/"):
            path = path[1:]
        method_to_call = getattr(self, "run_" + path, None)
        if method_to_call is None:
            self.send_error(404, "File %s not found" % path)
        else:
            method_to_call()
    
    do_POST = do_GET
    
    def run_(self):
        self.run_index()
    
    def run_index(self):
        self.serve_data("text/html", HTML_PAGE)
    
    def run_some_callback(self):
        import time
        
        time.sleep(1)
        self.server.counter += 1
        self.serve_data("text/json", "{'counter':%d}" % self.server.counter)
    
    def run_jssource(self):
        fn = compile_function(runjs, [])
        self.serve_data("text/javascript", fn.source())
    
    def serve_data(self, content_type, data):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Content-length", len(data))
        self.end_headers()
        self.wfile.write(data)

def _main(server_class=Server,
          handler_class=RequestHandler):
    global httpd

    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    _main()
