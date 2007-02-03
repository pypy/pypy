
""" Server testing
"""

import py
from pypy.translator.js.lib import server
from urllib import URLopener
import os

class Handler(server.TestHandler):
    def index(self):
        return "xxx"
    index.exposed = True

def test_basic_startup():
    import thread
    # XXX: how to do this without threads?
    httpd = server.HTTPServer(('127.0.0.1', 21210), Handler)
    thread.start_new_thread(httpd.serve_forever, ())
    assert URLopener().open("http://127.0.0.1:21210/index").read() == "xxx"

def test_own_startup():
    server.start_server(server_address=('127.0.0.1', 21211),
                        handler=Handler, fork=True)
    assert URLopener().open("http://127.0.0.1:21210/index").read() == "xxx"

def test_static_page():
    import thread
    tmpdir = py.test.ensuretemp("server_static_page")
    tmpdir.ensure("test.html").write("<html></html>")
    
    class StaticHandler(server.TestHandler):
        static_dir = str(tmpdir)
        index = server.Static(os.path.join(static_dir, "test.html"))

    httpd = server.HTTPServer(('127.0.0.1', 21212), StaticHandler)
    thread.start_new_thread(httpd.serve_forever, ())
    assert URLopener().open("http://127.0.0.1:21212/index").read() == \
           "<html></html>"
