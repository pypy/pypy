
#from pypeers.pipe.gsocket import GreenSocket
from socket import socket
from py.__.net.msgstruct import decodemessage, message
from socket import socket, AF_INET, SOCK_STREAM
import marshal
import sys

TRACE = False
def trace(msg):
    if TRACE:
        print >>sys.stderr, msg

class SocketWrapper(object):
    def __init__(self, conn):
        self.buffer = ""
        self.conn = conn

    def receive(self):
        msg, self.buffer = decodemessage(self.buffer)
        while msg is None:
            self.buffer += self.conn.recv(8192)
            msg, self.buffer = decodemessage(self.buffer)
        assert msg[0] == 'c'
        trace("received %s" % msg[1])
        return marshal.loads(msg[1])

    def send(self, data):
        trace("sending %s" % (data,))
        self.conn.sendall(message('c', marshal.dumps(data)))
        trace("done")

def socket_listener(address=('', 12122)):
    s = socket(AF_INET, SOCK_STREAM)
    s.bind(address)
    s.listen(1)
    print "Waiting for connection"
    conn, addr = s.accept()

    sw = SocketWrapper(conn)
    return sw.send, sw.receive

def socket_connecter(address):
    s = socket(AF_INET, SOCK_STREAM)
    print "Connecting %s" % (address,)
    s.connect(address)

    sw = SocketWrapper(s)
    return sw.send, sw.receive
