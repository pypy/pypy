
from distributed import RemoteProtocol, remote_loop

class X:
    def __init__(self, z):
        self.z = z
        
    def meth(self, x):
        return self.z + x()

    def raising(self):
        1/0
        
x = X(3)

def remote():
    from distributed.socklayer import socket_listener
    send, receive = socket_listener()
    remote_loop(RemoteProtocol(send, receive, globals()))

def local():
    from distributed.socklayer import socket_connecter
    send, receive = socket_connecter(('localhost', 12121))
    return RemoteProtocol(send, receive)

import sys
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-r':
        remote()
    else:
        rp = local()
        x = rp.get_remote("x")
        try:
            x.raising()
        except:
            import sys
            import pdb
            pdb.post_mortem(sys.exc_info()[2])
