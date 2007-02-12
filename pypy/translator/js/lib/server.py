
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
        path = self.path
        if path.endswith("/"):
            path = path[:-1]
        if path.startswith("/"):
            path = path[1:]
        m = re.match('^(.*)\?(.*)$', path)
        if m:
            path = m.group(1)
            getargs = m.group(2)
        else:
            getargs = ""
        name_path = path.replace(".", "_")
        if name_path == "":
            name_path = "index"
        method_to_call = getattr(self, name_path, None)
        if method_to_call is None or not getattr(method_to_call, 'exposed', None):
            exec_meth = getattr(self.exported_methods, name_path, None)
            if exec_meth is None:
                self.send_error(404, "File %s not found" % path)
            else:
                self.serve_data('text/json', json.write(exec_meth(**self.parse_args(getargs))))
        else:
            outp = method_to_call(**self.parse_args(getargs))
            if isinstance(outp, (str, unicode)):
                self.serve_data('text/html', outp)
            elif isinstance(outp, tuple):
                self.serve_data(*outp)
            else:
                raise ValueError("Don't know how to serve %s" % (outp,))
    
    def parse_args(self, getargs):
        # parse get argument list
        if getargs == "":
            return {}
        
        args = {}
        arg_pairs = getargs.split("&")
        for arg in arg_pairs:
            key, value = arg.split("=")
            args[key] = value
        return args
    
    def log_message(self, format, *args):
        # XXX just discard it
        pass
    
    do_POST = do_GET
    
    def serve_data(self, content_type, data):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Content-length", len(data))
        self.end_headers()
        self.wfile.write(data)

class Static(object):
    exposed = True
    
    def __init__(self, path=None):
        self.path = path

    def __call__(self):
        return open(self.path).read()

def start_server(server_address = ('', 8000), handler=TestHandler, fork=False,
                 timeout=None, server=HTTPServer, port_file=None):
    patch_handler(handler)
    httpd = server(server_address, handler)
    if timeout:
        def f(httpd):
            while 1:
                time.sleep(.3)
                if time.time() - httpd.last_activity > timeout:
                    httpd.server_close()
                    import os
                    os.kill(os.getpid(), 15)
        import thread
        thread.start_new_thread(f, (httpd,))
    httpd.last_activity = time.time()

    print "Server started, listening on %s:%s" %\
          (httpd.server_address[0],httpd.server_port)
    if port_file:
        # this is strange hack to allow exchange of port information
        py.path.local(port_file).write(str(httpd.server_port))
    if fork:
        import thread
        thread.start_new_thread(httpd.serve_forever, ())
        return httpd
    else:
        httpd.serve_forever()

Handler = TestHandler
# deprecate TestHandler name
