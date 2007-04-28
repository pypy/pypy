""" This is sample demo about how flexible pypy distribution is.
Not counting __doc__ and initialization this is 2 line,
fully operational file server,
sample client which is in fileclient.py is included as well.

Note that you must run it with pypy-c compiled with transparent proxy
and allworkingmodules (or at least socket and select)
"""

HOST = '127.0.0.1' # defaults to localhost, not to export your files
PORT = 12221

from distributed.socklayer import socket_loop
socket_loop((HOST, PORT), {'open':open})
