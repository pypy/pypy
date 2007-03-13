"""
An extension to py.execnet to allow multiple programs to exchange information
via a common server.  The idea is that all programs first open a gateway to
the same server (e.g. an SshGateway), and then call the conference() function
with a local TCP port number.  The first program must pass is_server=True and
the next ones is_server=False: the first program's remote gateway is used as
shared server for the next ones.

For all programs, the conference() call returns a new gateway that is
connected to the Python process of this shared server.  Information can
be exchanged by passing data around within this Python process.
"""
import py
from py.__.execnet.register import InstallableGateway


def conference(gateway, port, is_server='auto'):
    if is_server:    # True or 'auto'
        channel = gateway.remote_exec(r"""
            import thread
            from socket import *
            s = socket(AF_INET, SOCK_STREAM)
            port = channel.receive()
            try:
                s.bind(('', port))
                s.listen(5)
            except error:
                channel.send(0)
            else:
                channel.send(1)

                def readall(s, n):
                    result = ''
                    while len(result) < n:
                        t = s.read(n-len(result))
                        if not t:
                            raise EOFError
                        result += t
                    return result

                def handle_connexion(clientsock, address):
                    clientfile = clientsock.makefile('r+b',0)
                    source = clientfile.readline().rstrip()
                    clientfile.close()
                    g = {'clientsock' : clientsock, 'address' : address}
                    source = eval(source)
                    if source:
                        g = {'clientsock' : clientsock, 'address' : address}
                        co = compile(source+'\n', source, 'exec')
                        exec co in g

                while True:
                    conn, addr = s.accept()
                    if addr[0] == '127.0.0.1':   # else connexion refused
                        thread.start_new_thread(handle_connexion, (conn, addr))
                    del conn
        """)
        channel.send(port)
        ok = channel.receive()
        if ok:
            return gateway
        if is_server == 'auto':
            pass   # fall-through and try as a client
        else:
            raise IOError("cannot listen on port %d (already in use?)" % port)

    if 1:   # client
        channel = gateway.remote_exec(r"""
            import thread
            from socket import *
            s = socket(AF_INET, SOCK_STREAM)
            port = channel.receive()
            s.connect(('', port))
            channel.send(1)
            def receiver(s, channel):
                while True:
                    data = s.recv(4096)
                    #print >> open('LOG','a'), 'backward', repr(data)
                    channel.send(data)
                    if not data: break
            thread.start_new_thread(receiver, (s, channel))
            try:
                for data in channel:
                    #print >> open('LOG','a'), 'forward', repr(data)
                    s.sendall(data)
            finally:
                s.shutdown(1)
        """)
        channel.send(port)
        ok = channel.receive()
        assert ok
        return InstallableGateway(ConferenceChannelIO(channel))


class ConferenceChannelIO:
    server_stmt = """
io = SocketIO(clientsock)
"""

    error = (EOFError,)

    def __init__(self, channel):
        self.channel = channel
        self.buffer = ''

    def read(self, numbytes):
        #print >> open('LOG', 'a'), 'read %d bytes' % numbytes
        while len(self.buffer) < numbytes:
            t = self.channel.receive()
            if not t:
                #print >> open('LOG', 'a'), 'EOFError'
                raise EOFError
            self.buffer += t
        buf, self.buffer = self.buffer[:numbytes], self.buffer[numbytes:]
        #print >> open('LOG', 'a'), '--->', repr(buf)
        return buf

    def write(self, data):
        #print >> open('LOG', 'a'), 'write(%r)' % (data,)
        self.channel.send(data)

    def close_read(self):
        pass

    def close_write(self):
        self.channel.close()
