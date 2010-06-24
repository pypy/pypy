import sys
import socket

from rpyc import connect, SlaveService
from rpyc.utils.classic import DEFAULT_SERVER_PORT

try:
    conn = connect("localhost", DEFAULT_SERVER_PORT, SlaveService,
           config=dict(call_by_value_for_builtin_mutable_types=True))
except socket.error, e:
    raise ImportError("Error while connecting: " + str(e))


remote_eval = conn.eval


def proxy_module(globals):
    module = getattr(conn.modules, globals["__name__"])
    for name in module.__dict__.keys():
        globals[name] = getattr(module, name)

def proxy_sub_module(globals, name):
    fullname = globals["__name__"] + "." + name
    sys.modules[fullname] = globals[name] = conn.modules[fullname]
