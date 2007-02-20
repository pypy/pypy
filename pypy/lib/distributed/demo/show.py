""" Notes: you need to have pylib, greenexecnet, greensock2 and pypeers
symlinked in pypy/lib dir
"""

import sys
import greenexecnet
import py

remote = py.code.Source("""
class X:
    def __init__(self, z):
        self.z = z
        
    def meth(self, x):
        return self.z + x()

    def raising(self):
        1/0
        
x = X(3)

from distributed import RemoteProtocol, remote_loop
remote_loop(RemoteProtocol(channel.send, channel.receive, {'x':x}))
""")

if __name__ == '__main__':
    gw = greenexecnet.SshGateway('localhost', remotepython=sys.executable)
    ch = gw.remote_exec(str(remote))
    from distributed import RemoteProtocol
    rp = RemoteProtocol(ch.send, ch.receive, {})
    x = rp.get_remote("x")

    # examples:
    # def f():
    #    return 3
    # x.meth(f) # should be 3 + 3, but f called locally

    # try:
    #   x.raising
    # except:
    #   import sys
    #   e = sys.exc_info()
    # e[2].tb_next.tb_next.tb_frame.f_locals['self'].z
    # # should be 3 (remote z), note that one frame is not cut properly
    
    import code
    code.interact(local=locals())
