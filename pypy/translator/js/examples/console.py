
import subprocess
import fcntl
import os
import py
import time

from pypy.translator.js.lib import server
from pypy.translator.js.main import rpython2javascript
from pypy.translator.js.lib.support import callback
from pypy.translator.js import commproxy

commproxy.USE_MOCHIKIT = True

FUNCTION_LIST = ["console_onload"]


def js_source():
    import console_client
    return rpython2javascript(console_client, FUNCTION_LIST)

def run_console(python):
    pipe = subprocess.Popen([python, "-u", "-i"], stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE, stderr=subprocess.STDOUT,
                            close_fds=True, bufsize=0)
    # a bit of a POSIX voodoo
    fcntl.fcntl(pipe.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
    return pipe

def interact(pipe, to_write=None):
    if to_write is not None:
        pipe.stdin.write(to_write + "\n")
    try:
        return pipe.stdout.read()
    except IOError:
        time.sleep(.1)
        return ""

class Sessions(object):
    def __init__(self):
        self.sessions = {}

    def new_session(self):
        pipe = run_console("python")
        self.sessions[pipe.pid] = pipe
        return pipe.pid

    def update_session(self, pid, to_write=None):
        pipe = self.sessions[pid]
        return interact(pipe, to_write)

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
        try:
            return ["refresh", sessions.update_session(int(pid), to_write)]
        except KeyError:
            return ["disconnected"]

    @callback(retval=[str])
    def refresh_empty(self, pid=0):
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
