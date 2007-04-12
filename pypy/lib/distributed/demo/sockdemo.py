
from distributed import RemoteProtocol, remote_loop
from distributed.socklayer import Finished, socket_listener, socket_connecter

PORT = 12122

class X:
    def __init__(self, z):
        self.z = z
        
    def meth(self, x):
        return self.z + x()

    def raising(self):
        1/0

x = X(3)

def remote():
    send, receive = socket_listener(address=('', PORT))
    remote_loop(RemoteProtocol(send, receive, globals()))

def local():
    send, receive = socket_connecter(('localhost', PORT))
    return RemoteProtocol(send, receive)

import sys
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-r':
        try:
            remote()
        except Finished:
            print "Finished"
    else:
        rp = local()
        x = rp.get_remote("x")
        try:
            x.raising()
        except:
            import sys
            import pdb
            pdb.post_mortem(sys.exc_info()[2])
