"""
   This is an example usage of the 'thunk' object space of PyPy.
   It implements transparent distributed object manipulation.

   Start a server on a local port, say port 8888, with:

       $ py.py -o thunk sharedref.py 8888
       Waiting for connection on port 8888

   Then start and connect a client from the same or another machine:

       $ py.py -o thunk sharedref.py ip_or_name:8888
       Connecting to ('...', 8888)
       Ok
       >>> l = [1,2,3]
       >>> chan.send(l)    # send the list to the server over the connexion

   On the server-side:

       Connected from ('...', 1046)
       >>> l = chan.recv()    # receive the list sent above
       >>> l
       [1, 2, 3]
       >>> l.append(4)

   Back on the client-side:

       >>> l
       [1, 2, 3, 4]

   The list behaves like a single distributed object, which both sides can
   modify and access without needing further explicit synchronization.
   There is no difference between who was the original sender or receiver of
   the object, nor between which side was originally 'server' or 'client'.
"""

import sys, marshal
from __pypy__ import thunk, become
from socket import *
from select import select


class Channel:

    def __init__(self, s, serverside):
        # invariants: a shared object 'obj' is
        #  - either remote, and a thunk, and not a value in self.cache
        #  - or local (or at least on "our" side of this Channel), and
        #    then it has a corresponding key in self.cache
        self.s = s
        self.cache = {}
        self.inputfifo = []
        self.count = int(not serverside)

##    def _check(self, obj):
##        print '%s: cache=%r' % (self, self.cache.keys()),
##        if is_thunk(obj):
##            print 'THUNK'
##        else:
##            print obj

    def sendraw(self, obj):
        data = marshal.dumps(obj)
        hdr = str(len(data))
        hdr = '0'*(10-len(hdr)) + hdr
        self.s.sendall(hdr + data)

    def _readbytes(self, count):
        data = ''
        while len(data) < count:
            t = self.s.recv(count - len(data))
            if not t:
                raise EOFError
            data += t
        return data

    def recvraw(self):
        datasize = int(self._readbytes(10))
        data = self._readbytes(datasize)
        return marshal.loads(data)

    def send(self, obj, n=None):
        #print 'send', n,; self._check(obj)
        if n is None:
            n = self.count
            self.count += 2
            data = (n, obj, None)
        else:
            data = (n, obj)
        self.sendraw(data)
        become(obj, thunk(self._resume, n))
        #print 'done', n,; self._check(obj)

    def recv(self):
        obj = self.inputfifo.pop(0)
        #print 'recv',; self._check(obj)
        return obj

    def _resume(self, n):
        #print 'resume', n,; sys.stdout.flush()
        assert n not in self.cache
        self.sendraw((n,))
        while n not in self.cache:
            self.handle_once()
        obj = self.cache[n]
        #self._check(obj)
        return obj

    def handle_once(self):
        input = self.recvraw()
        if len(input) > 1:
            obj = input[1]
            self.cache[input[0]] = obj
            if len(input) > 2:
                self.inputfifo.append(obj)
        else:
            n = input[0]
            obj = self.cache[n]
            self.send(obj, n)
            del self.cache[n]


def mainloop(channels):
    stdin = sys.stdin.fileno()
    sockfd = [chan.s.fileno() for chan in channels]
    while True:
        sys.stdout.write('>>> ')
        sys.stdout.flush()
        while True:
            iwtd, owtd, ewtd = select([stdin] + sockfd, [], [stdin])
            if stdin in iwtd or stdin in ewtd: break
            for chan in channels:
                if chan.s.fileno() in iwtd:
                    chan.handle_once()
        code = raw_input()
        if not code: break
        try:
            co = compile(code, '<input>', 'single')
            exec co in globals()
        except Exception, e:
            print e.__class__.__name__, str(e)


def server(port):
    s = socket(AF_INET, SOCK_STREAM)
    s.bind(('', port))
    s.listen(1)
    print 'Waiting for connection on port', port
    s, addr = s.accept()
    print 'Connected from', addr
    return Channel(s, True)

def client(addr):
    s = socket(AF_INET, SOCK_STREAM)
    print 'Connecting to', addr
    s.connect(addr)
    print 'Ok'
    return Channel(s, False)


if __name__ == '__main__':
    try:
        thunk, become    # only available in 'py.py -o thunk'
    except NameError:
        print __doc__
        raise SystemExit(2)

    channels = []
    for a in sys.argv[1:]:
        try:
            port = int(a)
        except ValueError:
            host, port = a.split(':')
            port = int(port)
            chan = client((host, port))
        else:
            chan = server(port)
        channels.append(chan)

    mainloop(channels)
