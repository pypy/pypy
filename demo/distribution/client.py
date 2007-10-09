""" This a sample client, suitable for use with server.py from this
directory

run by:
pypy-c client.py
"""

HOST = '127.0.0.1'
PORT = 12222

from distributed.socklayer import connect
remote_handle = connect((HOST, PORT))

import code
code.interact(local=locals())

""" Things that can be done: 1. remote object access

x = remote_handle.x
assert type(x) is remote_handle.X # typecheck
x.meth(lambda x: x + 10, 6) # remote call, with callback localy
x.meth(remote_handle.f, 3) # remote call, remote callback
remote_handle.sys._getframe(2).f_locals['x'] # remote frame access
# XXX should be 'is x' and shouldn't need (2) argument

# XXX next one does not work, while it should. Too much mangling with remote
# traceback frames probably
try:
  x.meth(1, 2) # non-callable argument, AssertionError
except:
  import sys
  e, c, tb = sys.exc_info()
  import pdb
  pdb.post_mortem(tb)
"""
