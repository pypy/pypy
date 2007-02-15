#!/usr/bin/env python
""" This is script which collects all the demos and
run them when needed
"""

import autopath

from pypy.translator.js.lib import server
from pypy.translator.js.lib.support import callback
from pypy.rpython.extfunc import _callable
from pypy.rpython.ootypesystem.bltregistry import described
from pypy.translator.js.main import rpython2javascript

import os
import py

FUNCTION_LIST = ['launch_console', 'bnb_redirect']
TIMEOUT = 300
pids = []

def launch_console_in_new_prcess():
    from pypy.translator.js.examples import pythonconsole
    httpd = server.create_server(server_address=('', 0),
                        handler=pythonconsole.RequestHandler,
                        server=pythonconsole.Server)
    port = httpd.server_port
    pythonconsole.httpd = httpd
    pid = server.start_server_in_new_process(httpd, timeout=TIMEOUT)
    del httpd
    pids.append(pid)
    return port

class ExportedMethods(server.ExportedMethods):
    @callback(retval=int)
    def launch_console(self):
        """ Note that we rely here on threads not being invoked,
        if we want to make this multiplayer, we need additional locking
        XXX
        """
        return launch_console_in_new_prcess()

exported_methods = ExportedMethods()

def js_source(function_list):
    import over_client
    return rpython2javascript(over_client, FUNCTION_LIST)

class Handler(server.Handler):
    static_dir = str(py.path.local(__file__).dirpath().join("data"))
    index = server.Static()
    console = server.Static(os.path.join(static_dir, "launcher.html"))
    terminal = server.Static(os.path.join(static_dir, "terminal.html"))
    exported_methods = exported_methods

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

if __name__ == '__main__':
    try:
        addr = ('', 8008)
        httpd = server.create_server(server_address=addr, handler=Handler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        for pid in pids:
            # eventually os.kill stuff
            os.kill(pid, 15)
            os.waitpid(pid, 0)

