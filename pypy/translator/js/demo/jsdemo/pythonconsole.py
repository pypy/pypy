#!/usr/bin/env python
""" A basic Python console from your browser.

This depends on MochiKit for proper quoting.
You need to provide the files as ..jsdemo/MochiKit/*.js.
(Symlinks are your friends.)

Try to type:  import time; time.sleep(2); print 'hi'
"""

import autopath

import new, sys, os, cStringIO
from cgi import parse_qs
from pypy.translator.js.modules._dom import setTimeout, get_document
from pypy.translator.js.main import rpython2javascript
from pypy.rpython.ootypesystem.bltregistry import MethodDesc, BasicExternal
from pypy.translator.js import commproxy
from pypy.translator.js.modules.mochikit import createLoggingPane, log

commproxy.USE_MOCHIKIT = True

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
#from SimpleHTTPServer import SimpleHTTPRequestHandler

def js_source(functions):
    mod = new.module('_js_src')
    function_names = []
    for func in functions:
        name = func.__name__
        if hasattr(mod, name):
            raise ValueError("exported function name %r is duplicated"
                             % (name,))
        mod.__dict__[name] = func
        function_names.append(name)
    sys.modules['_js_src'] = mod
    try:
        return rpython2javascript(mod, function_names)
    finally:
        del sys.modules['_js_src']

# ____________________________________________________________

HTML_PAGE = """
<html>
<head>
  <title>Example</title>
  <script type="text/javascript" src="jssource"/>
  <script src="MochiKit/MochiKit.js" type="text/javascript"/>
</head>
<body onload="setup_page()">
<h3>Console</h3>

    <pre id="data"></pre>

    <input id="inp" size="100" type="text"/>

</body>
</html>
"""

httpd = None

def callback(data):
    inp_elem = get_document().getElementById("inp")
    inp_elem.disabled = False
    answer = data.get('answer', '')
    add_text(answer)

def add_text(text):
    data_elem = get_document().getElementById("data")
    data_elem.innerHTML += text

class Storage(object):
    def __init__(self):
        self.level = 0
        self.cmd = ""

storage = Storage()

def keypressed(key):
    kc = key.keyCode
    if kc == ord("\r"):
        inp_elem = get_document().getElementById("inp")
        cmd = inp_elem.value
        add_text(">>> %s\n" % (cmd,))
        inp_elem.value = ''
        storage.cmd += cmd + "\n"
        if cmd.endswith(':'):
            storage.level += 1
        elif storage.level == 0:
            inp_elem.disabled = True
            httpd.some_callback(storage.cmd, callback)
            storage.cmd = ""
        else:
            storage.level -= 1

def setup_page():
    createLoggingPane(True)
    get_document().onkeypress = keypressed

class Server(HTTPServer, BasicExternal):
    # Methods and signatures how they are rendered for JS
    _methods = {
        'some_callback' : MethodDesc([('cmd', "aa"),
                                      ('callback', lambda : None)],
                                     {'aa': 'aa'})
    }
    
    _render_xmlhttp = True
    
    def __init__(self, *args, **kwargs):
        HTTPServer.__init__(self, *args, **kwargs)
        self.source = None
        self.locals = {}

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        if '?' in path:
            i = path.index('?')
        else:
            i = len(path)
        kwds = parse_qs(path[i+1:])
        path = path[:i].split("/")
        if not path[0]:
            del path[0]
        if not path:
            path = ['']
        cmd = path[0]
        args = path[1:]
        method_to_call = getattr(self, "run_" + cmd, None)
        if method_to_call is None:
            self.send_error(404, "File %r not found" % (self.path,))
        else:
            method_to_call(*args, **kwds)
    
    do_POST = do_GET
    
    def run_(self):
        self.run_index()
    
    def run_index(self):
        self.serve_data("text/html", HTML_PAGE)

    def run_MochiKit(self, filename):
        assert filename in os.listdir('MochiKit')
        pathname = os.path.join('MochiKit', filename)
        f = open(pathname, 'r')
        data = f.read()
        f.close()
        self.serve_data("text/javascript", data)
    
    def run_some_callback(self, cmd=[""]):
        cmd = cmd[0]
        if cmd:
            buf = cStringIO.StringIO()
            out1 = sys.stdout
            err1 = sys.stderr
            try:
                sys.stdout = sys.stderr = buf
                try:
                    exec compile(cmd, '?', 'single') in self.server.locals
                except Exception:
                    import traceback
                    traceback.print_exc()
            finally:
                sys.stdout = out1
                sys.stderr = err1
            answer = buf.getvalue()
        else:
            answer = ""
        self.serve_data("text/json", repr({'answer': answer}))
    
    def run_jssource(self):
        if self.server.source:
            source = self.server.source
        else:
            source = js_source([setup_page])
            self.server.source = source
        self.serve_data("text/javascript", source)
    
    def serve_data(self, content_type, data):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Content-length", len(data))
        self.end_headers()
        self.wfile.write(data)

def _main(server_class=Server,
          handler_class=RequestHandler):
    global httpd

    server_address = ('127.0.0.1', 8000)
    httpd = server_class(server_address, handler_class)
    print 'http://127.0.0.1:%d' % (server_address[1],)
    httpd.serve_forever()

if __name__ == '__main__':
    _main()
