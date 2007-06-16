#!/usr/bin/env python
""" A basic Python console from your browser.

This depends on MochiKit for proper quoting.
You need to provide the files as ..jsdemo/MochiKit/*.js.
(Symlinks are your friends.)

Try to type:  import time; time.sleep(2); print 'hi'
"""

import autopath

import sys, os, cStringIO
from cgi import parse_qs
from pypy.translator.js.modules.dom import setTimeout, document, window
from pypy.translator.js.modules.mochikit import connect, disconnect
from pypy.rpython.ootypesystem.bltregistry import MethodDesc, BasicExternal
from pypy.translator.js import commproxy
from pypy.rpython.extfunc import genericcallable

from pypy.translator.js.lib import support
from pypy.translator.js.lib import server

commproxy.USE_MOCHIKIT = True

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
import time

HTML_PAGE = """
<html>
<head>
  <title>Example</title>
  <script type="text/javascript" src="jssource"></script>
  <script src="http://mochikit.com/MochiKit/MochiKit.js" type="text/javascript"></script>
</head>
<body onload="setup_page()">
<h3>Console</h3>
<p>Note that a default timeout for the console is 5 minutes, after that time
console just dies and stops responding</p>

    <div id="data"></div>

    <input id="inp" size="100" type="text" autocomplete="off"/>

</body>
</html>
"""

httpd = None

def callback(data):
    inp_elem = document.getElementById("inp")
    inp_elem.disabled = False
    answer = data.get('answer', '')
    add_text(answer)
    inp_elem.focus()

def add_text(text):
    data_elem = document.getElementById("data")
    lines = text.split('\n')
    lines.pop()
    for line in lines:
        pre = document.createElement('pre')
        pre.style.margin = '0px'
        pre.appendChild(document.createTextNode(line))
        data_elem.appendChild(pre)

class Storage(object):
    def __init__(self):
        self.level = 0
        self.cmd = ""

storage = Storage()

def keypressed(key):
    kc = key._event.keyCode
    if kc == ord("\r"):
        inp_elem = document.getElementById("inp")
        cmd = inp_elem.value
        if storage.level == 0:
            add_text(">>> %s\n" % (cmd,))
        else:
            add_text("... %s\n" % (cmd,))
        inp_elem.value = ''
        if cmd:
            storage.cmd += cmd + "\n"
        if cmd.endswith(':'):
            storage.level = 1
        elif storage.level == 0 or cmd == "":
            if (not storage.level) or (not cmd):
                inp_elem.disabled = True
                httpd.some_callback(storage.cmd, callback)
                storage.cmd = ""
                storage.level = 0

def setup_page():
    connect(document, 'onkeypress', keypressed)
    document.getElementById("inp").focus()

class Server(HTTPServer, BasicExternal):
    # Methods and signatures how they are rendered for JS
    _methods = {
        'some_callback' : MethodDesc([('cmd', str),
                          ('callback', genericcallable([{str:str}]))],
                           {str:str})
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
        self.server.last_activity = time.time()
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
            source = support.js_source([setup_page])
            self.server.source = source
        self.serve_data("text/javascript", source)
    
    def serve_data(self, content_type, data):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Content-length", len(data))
        self.send_header('Expires', 'Mon, 26 Jul 1997 05:00:00 GMT')
        self.send_header('Last-Modified',
                         time.strftime("%a, %d %b %Y %H:%M:%S GMT"))
        self.send_header('Cache-Control', 'no-cache, must-revalidate')
        self.send_header('Cache-Control', 'post-check=0, pre-check=0')
        self.send_header('Pragma', 'no-cache')
        self.end_headers()
        self.wfile.write(data)


def build_http_server(server_address=('', 8001)):
    global httpd
    httpd = Server(server_address, RequestHandler)
    print 'http://127.0.0.1:%d' % (server_address[1],)

def _main(address=('', 8001)):
    build_http_server(server_address=address)
    httpd.serve_forever()

if __name__ == '__main__':
    _main()
