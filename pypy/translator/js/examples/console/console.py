
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
from py.__.green.server.httpserver import GreenHTTPServer

commproxy.USE_MOCHIKIT = True

FUNCTION_LIST = ["load_console", "console_onload"]

class Ignore(Exception):
    pass

def js_source():
    import client
    return rpython2javascript(client, FUNCTION_LIST)

def line_split(ret, max_len):
    to_ret = []
    for line in ret.split("\n"):
        if len(line) > max_len:
            to_ret += [line[i*max_len:(i+1)*max_len] for i in
                       range(len(line)/max_len - 1)]
            i += 1
        else:
            i = 0
        to_ret.append(line[i*max_len:])
    return "\n".join(to_ret)


STATIC_DIR = py.path.local(__file__)
for x in range(6):
    STATIC_DIR = STATIC_DIR.dirpath()
STATIC_DIR = STATIC_DIR.join("compiled")

class Sessions(object):
    def __init__(self):
        self.sessions = {}
        self.updating = {}

    def new_session(self, python="python"):
        if not py.path.local().sysfind(python):
            python = str(STATIC_DIR.join(python))
        ip = Interpreter(python)
        self.sessions[ip.pid] = ip
        self.updating[ip.pid] = False
        return ip.pid

    def update_session(self, pid, to_write=None):
        ip = self.sessions[pid]
        if self.updating[pid]:
            ip.write_only(to_write)
            raise Ignore()
        self.updating[pid] = True
        ret = ip.interact(to_write)
        self.updating[pid] = False
        if not ret:
            return ""
        MAX_LEN = 80
        return line_split(ret, MAX_LEN)

    def kill_session(self, pid):
        ip = self.sessions[pid]
        ip.pipe.stdin.close()
        del self.sessions[pid]
        del self.updating[pid]

# We hack here, cause in exposed methods we don't have global 'server'
# state
sessions = Sessions()

class ExportedMethods(server.ExportedMethods):
    @callback(args=[str], retval=int)
    def get_console(self, python="python"):
        retval = sessions.new_session(python)
        return retval

    @callback(retval=[str])
    def refresh(self, pid=0, to_write=""):
        #print "Refresh %s %d" % (to_write, int(pid))
        try:
            return ["refresh", sessions.update_session(int(pid), to_write)]
        except (KeyError, IOError):
            return ["disconnected"]
        except Ignore:
            return ["ignore"]

    @callback(retval=[str])
    def refresh_empty(self, pid=0):
        #print "Empty refresh %d" % int(pid)
        try:
            return ["refresh", sessions.update_session(int(pid), None)]
        except (KeyError, IOError):
            return ["disconnected"]
        except Ignore:
            return ["ignore"]

    @callback()
    def kill_console(self, pid=0):
        sessions.kill_session(int(pid))

exported_methods = ExportedMethods()

static_dir = py.path.local(__file__).dirpath().join("data")

class Root(server.Collection):
    exported_methods = exported_methods
    #index = server.Static(static_dir.join("console.html"))
    index = server.FsFile(static_dir.join("console.html"))
    MochiKit = server.StaticDir('MochiKit')

    def source_js(self):
        if hasattr(self.server, 'source_console'):
            source = self.server.source_console
        else:
            source = js_source()
            self.server.source_console = source
        return "text/javascript", source
    source_js.exposed = True

class Handler(server.NewHandler):
    application = Root()
    application.some = Root()
    application.other = Root()

if __name__ == '__main__':
    addr = ('', 8007)
    httpd = server.create_server(server_address=addr, handler=Handler,
                                 server=GreenHTTPServer)
    httpd.serve_forever()
