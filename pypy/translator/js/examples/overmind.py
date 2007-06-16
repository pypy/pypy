#!/usr/bin/env python
""" This is script which collects all the demos and
run them when needed
"""

import autopath

from pypy.translator.js.lib import server
from pypy.translator.js.lib.support import callback
from pypy.rpython.ootypesystem.bltregistry import described
from pypy.translator.js.main import rpython2javascript
from pypy.translator.js.examples.console import console
from py.__.green.server.httpserver import GreenHTTPServer

import os
import py

FUNCTION_LIST = ['bnb_redirect']
TIMEOUT = 300
pids = []

def js_source(function_list):
    import over_client
    return rpython2javascript(over_client, FUNCTION_LIST)

static_dir = py.path.local(__file__).dirpath().join("data")

class Root(server.Collection):
    index = server.FsFile(static_dir.join("index.html"))
    style_css = server.FsFile(static_dir.join("style.css"),
                              content_type="text/css")
    terminal = server.Static(static_dir.join("terminal.html"))
    console = console.Root()
    py_web1_png = server.FsFile(static_dir.join("py-web1.png"),
                                content_type="image/png")

    def source_js(self):
        if hasattr(self.server, 'source'):
            source = self.server.source
        else:
            source = js_source(FUNCTION_LIST)
            self.server.source = source
        return "text/javascript", source
    source_js.exposed = True

    def bnb(self):
        return '''
        <html>
           <head>
              <script src="source.js"></script>
           </head>
           <body onload="bnb_redirect()">
           </body>
        </html>'''
    bnb.exposed = True

    def handle_error(self, exc, e_value, tb):
        import traceback
        tb_formatted = '\n'.join(traceback.format_tb(tb)) + \
                       "%s: %s" % (exc, e_value)
        log_file = open("/tmp/play1_error_log", "a")
        log_file.write(tb_formatted)
        log_file.close()
        print tb_formatted

class Handler(server.NewHandler):
    application = Root()

    error_message_format = static_dir.join('error.html').read()
    #console = server.Static(os.path.join(static_dir, "launcher.html"))

if __name__ == '__main__':
    try:
        addr = ('', 8008)
        httpd = server.create_server(server_address=addr, handler=Handler,
                                     server=GreenHTTPServer)
        httpd.serve_forever()
    except KeyboardInterrupt:
        for pid in pids:
            # eventually os.kill stuff
            os.kill(pid, 15)
            os.waitpid(pid, 0)

