
""" This is sample client for a server based in fileserver.py, not counting
initialization, code.interact and __doc__ has just 2 lines! Usage:

pypy-c fileclient.py

The file_opener is a proxy for remote file object. Which means you can
perform same operations as locally, like file_opener('/etc/passwd').read()
or file_opener('/tmp/x', 'w').write('x')

pypy-c needs to be compiled with --allworkingmodules in order to have socket
working.
"""

HOST = '127.0.0.1'
PORT = 12221

from distributed.socklayer import connect
file_opener = connect((HOST, PORT)).open

import code
code.interact(local=locals())
# The file_opener is a proxy for remote file object. Which means you can
# perform same operations as locally, like file_opener('/etc/passwd').read()
# or file_opener('/tmp/x', 'w').write('x')
