
""" This is sample client for a server based in fileserver.py, not counting
initialization and __doc__ has just 2 lines. Usage:

pypy-c -i fileclient.py
"""
HOST = '127.0.0.1'
PORT = 12221

from distributed.socklayer import connect
file_opener = connect((HOST, PORT)).get_remote('open')

# now you can do for example file_opener('/etc/passwd').read() to
# read remote /etc/passwd
