
from pypeers.pipe.gsocket import GreenSocket
from socket import socket, AF_INET, SOCK_STREAM
import marshal
import sys

TRACE = False
def trace(msg):
    if TRACE:
        print >>sys.stderr, msg

def receive(conn):
    all = []
    data = conn.recv(10000)
    trace("received %s" % data)
    return marshal.loads(data)

def send(conn, data):
    trace("sending %s" % (data,))
    conn.send(marshal.dumps(data))
    trace("done")

def socket_listener(address=('', 12121)):
    s = GreenSocket(AF_INET, SOCK_STREAM)
    s.bind(address)
    s.listen(1)
    print "Waiting for connection"
    conn, addr = s.accept()
    
    return lambda data : send(conn, data), lambda : receive(conn)

def socket_connecter(address):
    s = GreenSocket(AF_INET, SOCK_STREAM)
    print "Connecting %s" % (address,)
    s.connect(address)

    return lambda data : send(s, data), lambda : receive(s)
