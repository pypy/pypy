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

