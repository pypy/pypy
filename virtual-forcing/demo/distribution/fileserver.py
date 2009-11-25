""" This is a sample demo showcasing file server, done by the pypy
distribution library.

Not counting __doc__ and initialization this is 2 line,
fully operational file server,
sample client which is in fileclient.py is included as well.

run by:
pypy-c fileserver.py

pypy-c needs to be compiled with --allworkingmodules in order to have socket
working.
"""

HOST = '127.0.0.1' # defaults to localhost, not to export your files
PORT = 12221

from distributed.socklayer import socket_loop
socket_loop((HOST, PORT), {'open':open})
