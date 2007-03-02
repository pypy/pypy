
""" This is example of totally basic server for XMLHttp request
built on top of BaseHTTPServer.

Construction is like that:

you take your own implementation of Handler and subclass it
to provide whatever you like. Each request is checked first for
apropriate method in handler (with dots replaced as _) and this method
needs to have set attribute exposed

If method is not there, we instead try to search exported_methods (attribute
of handler) for apropriate JSON call. We write down a JSON which we get as
a return value (note that right now arguments could be only strings) and
pass them to caller
"""

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

import re
import time
import random
import os
import sys

import py
from pypy.translator.js.lib.url import parse_url

from pypy.translator.js import json

from pypy.rpython.ootypesystem.bltregistry import MethodDesc, BasicExternal,\
    described
from pypy.translator.js.main import rpython2javascript
from pypy.translator.js import commproxy

commproxy.USE_MOCHIKIT = False

class ExportedMethods(BasicExternal):
    _render_xmlhttp = True

exported_methods = ExportedMethods()

def patch_handler(handler_class):
    """ This function takes care of adding necessary
    attributed to Static objects
    """
    for name, value in handler_class.__dict__.iteritems():
        if isinstance(value, Static) and value.path is None:
            assert hasattr(handler_class, "static_dir")
            value.path = os.path.join(str(handler_class.static_dir),
                                      name + ".html")

class TestHandler(BaseHTTPRequestHandler):
    exported_methods = exported_methods
    
    def do_GET(self):
        path, args = parse_url(self.path)
        if not path:
            path = ["index"]
        name_path = path[0].replace(".", "_")
        if len(path) > 1:
            rest = os.path.sep.join(path[1:])
        else:
            rest = None
        method_to_call = getattr(self, name_path, None)
        if method_to_call is None or not getattr(method_to_call, 'exposed', None):
            exec_meth = getattr(self.exported_methods, name_path, None)
            if exec_meth is None:
                self.send_error(404, "File %s not found" % path)
            else:
                self.serve_data('text/json', json.write(exec_meth(**args)),
                                True)
        else:
            if rest:
                outp = method_to_call(rest, **args)
            else:
                outp = method_to_call(**args)
            if isinstance(outp, (str, unicode)):
                self.serve_data('text/html', outp)
            elif isinstance(outp, tuple):
                self.serve_data(*outp)
            else:
                raise ValueError("Don't know how to serve %s" % (outp,))

    def log_message(self, format, *args):
        # XXX just discard it
        pass
    
    do_POST = do_GET
    
    def serve_data(self, content_type, data, nocache=False):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Content-length", len(data))
        if nocache:
            self.send_nocache_headers()
        self.end_headers()
        self.wfile.write(data)

    def send_nocache_headers(self):
        self.send_header('Expires', 'Mon, 26 Jul 1997 05:00:00 GMT')
        self.send_header('Last-Modified',
                         time.strftime("%a, %d %b %Y %H:%M:%S GMT"))
        self.send_header('Cache-Control', 'no-cache, must-revalidate')
        self.send_header('Cache-Control', 'post-check=0, pre-check=0')
        self.send_header('Pragma', 'no-cache')

class Static(object):
    exposed = True
    
    def __init__(self, path=None):
        self.path = path

    def __call__(self):
        return open(str(self.path)).read()

class StaticDir(object):
    exposed = True

    def __init__(self, path, type=None):
        self.path = path
        self.type = type

    def __call__(self, path):
        data = open(os.path.join(str(self.path), str(path))).read()
        if self.type:
            return self.type, data
        return data

def create_server(server_address = ('', 8000), handler=TestHandler,
                 server=HTTPServer):
    """ Parameters:
    spawn - create new thread and return (by default it doesn't return)
    fork - do a real fork
    timeout - kill process after X seconds (actually doesn't work for threads)
    port_file - function to be called with port number
    """
    patch_handler(handler)
    httpd = server(server_address, handler)
    httpd.last_activity = time.time()
    print "Server started, listening on %s:%s" %\
          (httpd.server_address[0],httpd.server_port)
    return httpd

def start_server_in_new_thread(server):
    import thread
    thread.start_new_thread(server.serve_forever, ())

def start_server_in_new_process(server, timeout=None):
    pid = os.fork()
    if not pid:
        if timeout:
            def f(httpd):
                while 1:
                    time.sleep(.3)
                    if time.time() - httpd.last_activity > timeout:
                        httpd.server_close()
                        import os
                        os.kill(os.getpid(), 15)
            import thread
            thread.start_new_thread(f, (server,))

        server.serve_forever()
        os._exit(0)
    return pid

Handler = TestHandler
# deprecate TestHandler name
