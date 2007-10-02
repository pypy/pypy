
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

class ReceiverWrapper(SocketWrapper):
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

class SenderWrapper(SocketWrapper):
    def send(self, data):
        trace("sending %s" % (data,))
        self.conn.sendall(message('c', marshal.dumps(data)))
        trace("done")

def socket_listener(address, socket=socket):
    s = socket(AF_INET, SOCK_STREAM)
    s.bind(address)
    s.listen(1)
    print "Waiting for connection on %s" % (address,)
    conn, addr = s.accept()
    print "Connected from %s" % (addr,)

    return SenderWrapper(conn).send, ReceiverWrapper(conn).receive

def socket_loop(address, to_export, socket=socket):
    from distributed import RemoteProtocol, remote_loop
    try:
        send, receive = socket_listener(address, socket)
        remote_loop(RemoteProtocol(send, receive, to_export))
    except Finished:
        pass

def socket_connecter(address, socket=socket):
    s = socket(AF_INET, SOCK_STREAM)
    print "Connecting %s" % (address,)
    s.connect(address)
    
    return SenderWrapper(s).send, ReceiverWrapper(s).receive

def connect(address, socket=socket):
    from distributed.support import RemoteView
    from distributed import RemoteProtocol
    return RemoteView(RemoteProtocol(*socket_connecter(address, socket)))

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
