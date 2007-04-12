
import py
from socket import socket
from py.__.green.msgstruct import decodemessage, message
from socket import socket, AF_INET, SOCK_STREAM
import marshal
import sys

TRACE = False
def trace(msg):
    if TRACE:
        print >>sys.stderr, msg

class Finished(Exception):
    pass

class SocketWrapper(object):
    def __init__(self, conn):
        self.buffer = ""
        self.conn = conn

    def receive(self):
        msg, self.buffer = decodemessage(self.buffer)
        while msg is None:
            data = self.conn.recv(8192)
            if not data:
                raise Finished()
            self.buffer += data
            msg, self.buffer = decodemessage(self.buffer)
        assert msg[0] == 'c'
        trace("received %s" % msg[1])
        return marshal.loads(msg[1])

    def send(self, data):
        trace("sending %s" % (data,))
        self.conn.sendall(message('c', marshal.dumps(data)))
        trace("done")

def socket_listener(address=('', 12122), socket=socket):
    s = socket(AF_INET, SOCK_STREAM)
    s.bind(address)
    s.listen(1)
    print "Waiting for connection"
    conn, addr = s.accept()

    sw = SocketWrapper(conn)
    return sw.send, sw.receive

def socket_connecter(address, socket=socket):
    s = socket(AF_INET, SOCK_STREAM)
    print "Connecting %s" % (address,)
    s.connect(address)

    sw = SocketWrapper(s)
    return sw.send, sw.receive

def spawn_remote_side(code, gw):
    """ A very simple wrapper around greenexecnet to allow
    spawning a remote side of lib/distributed
    """
    from distributed import RemoteProtocol
    extra = str(py.code.Source("""
    from distributed import remote_loop, RemoteProtocol
    remote_loop(RemoteProtocol(channel.send, channel.receive, globals()))
    """))
    channel = gw.remote_exec(code + "\n" + extra)
    return RemoteProtocol(channel.send, channel.receive)
