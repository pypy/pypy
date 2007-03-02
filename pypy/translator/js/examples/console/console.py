
import subprocess
import fcntl
import os
import py
import time

from pypy.translator.js.lib import server
from pypy.translator.js.main import rpython2javascript
from pypy.translator.js.lib.support import callback
from pypy.translator.js import commproxy
from pypy.translator.js.examples.console.session import Interpreter

commproxy.USE_MOCHIKIT = True

FUNCTION_LIST = ["console_onload"]


def js_source():
    import client
    return rpython2javascript(client, FUNCTION_LIST)

class Sessions(object):
    def __init__(self):
        self.sessions = {}

    def new_session(self):
        ip = Interpreter("python")
        self.sessions[ip.pid] = ip
        return ip.pid

    def update_session(self, pid, to_write=None):
        ip = self.sessions[pid]
        return ip.interact(to_write)

# We hack here, cause in exposed methods we don't have global 'server'
# state
sessions = Sessions()

class ExportedMethods(server.ExportedMethods):
    @callback(retval=int)
    def get_console(self):
        retval = sessions.new_session()
        return retval

    @callback(retval=[str])
    def refresh(self, pid=0, to_write=""):
        print "Refresh %s" % to_write
        try:
            return ["refresh", sessions.update_session(int(pid), to_write)]
        except KeyError:
            return ["disconnected"]

    @callback(retval=[str])
    def refresh_empty(self, pid=0):
        print "Empty refresh"
        try:
            return ["refresh", sessions.update_session(int(pid), None)]
        except KeyError:
            return ["disconnected"]
    

exported_methods = ExportedMethods()

class Handler(server.Handler):
    exported_methods = exported_methods
    static_dir = py.path.local(__file__).dirpath().join("data")
    index = server.Static(static_dir.join("console.html"))
    MochiKit = server.StaticDir('MochiKit')

    def source_js(self):
        if hasattr(self.server, 'source'):
            source = self.server.source
        else:
            source = js_source()
            self.server.source = source
        return "text/javascript", source
    source_js.exposed = True

if __name__ == '__main__':
    addr = ('', 8007)
    httpd = server.create_server(server_address=addr, handler=Handler)
    httpd.serve_forever()
