"""
port on socket, with write-queue-based writer thread and a reader-thread
"""

import autopath, sys, thread, struct, marshal, Queue

def recv_all(s, count):
    buf = ''
    while len(buf) < count:
        data = s.recv(count - len(buf))
        if not data:
            raise SystemExit   # thread exit, rather
        buf += data
    return buf

def recv_msg(s):
    hdr_size = struct.calcsize("!i")
    msg_size, = struct.unpack("!i", recv_all(s, hdr_size))
    msg = recv_all(s, msg_size)
    try:
        return marshal.loads(msg)
    except ValueError:
        # fall-back if Python 2.3 receives a 2.4 marshal format
        from pypy.lib._marshal import loads
        return loads(msg)

def send_msg(s, msg):
    data = marshal.dumps(msg)
    s.sendall(struct.pack("!i", len(data)) + data)


class Port:

    def __init__(self, s):
        self.s = s
        self.writeq = Queue.Queue()
        thread.start_new_thread(self.writer, ())
        thread.start_new_thread(self.reader, ())        

    def reader(self):
        while True:
            try:
                msg = recv_msg(self.s)
            except SystemExit:
                self.on_msg(None)
                raise SystemExit
            
            self.on_msg(msg)

    def on_msg(self, msg):
        pass

    def writer(self):
        while True:
            msg = self.writeq.get()
            if not msg:
                raise SystemExit
            send_msg(self.s, msg)

    def put_msg(self, msg):
        self.writeq.put(msg)


            
def run_server(port_factory, port=8888, quiet=False, background=False):
    import socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(('', port))
    server_sock.listen(5)
    if not quiet:
        print >> sys.stderr, 'Accepting connexions on port %d...' % port
    def accept_connexions():
        while True:
            conn, addr = server_sock.accept()
            if not quiet:
                print >> sys.stderr, 'Connected by %r.' % (addr,)
            port_factory(conn)
    if background:
        thread.start_new_thread(accept_connexions, ())
    else:
        accept_connexions()
