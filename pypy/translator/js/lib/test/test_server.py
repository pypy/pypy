
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
    assert URLopener().open("http://127.0.0.1:21210/").read() == "xxx"

def test_own_startup():
    httpd = server.create_server(server_address=('127.0.0.1', 21211),
                        handler=Handler)
    server.start_server_in_new_thread(httpd)
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

def test_static_page_implicit():
    import thread
    tmpdir = py.test.ensuretemp("server_static_page_implicit")
    tmpdir.ensure("index.html").write("<html></html>")
    
    class StaticHandler(server.TestHandler):
        static_dir = str(tmpdir)
        index = server.Static()

    server.patch_handler(StaticHandler)
    httpd = server.HTTPServer(('127.0.0.1', 21213), StaticHandler)
    thread.start_new_thread(httpd.serve_forever, ())
    assert URLopener().open("http://127.0.0.1:21213/index").read() == \
           "<html></html>"


def test_static_directory():
    py.test.skip("Fails")
    import thread
    tmpdir = py.test.ensuretemp("server_static_dir")
    tmpdir.ensure("a", dir=1)
    tmpdir.join("a").ensure("a.txt").write("aaa")
    tmpdir.join("a").ensure("b.txt").write("bbb")

    class StaticDir(server.Handler):
        static_dir = tmpdir
        a_dir = server.StaticDir(tmpdir.join("a"))

    httpd = server.HTTPServer(('127.0.0.1', 0), StaticDir)
    port = httpd.server_port
    thread.start_new_thread(httpd.serve_forever, ())
    addr = "http://127.0.0.1:%d/" % port
    assert URLopener().open(addr + "a_dir/a.txt").read() == "aaa"
    assert URLopener().open(addr + "a_dir/b.txt").read() == "bbb"

