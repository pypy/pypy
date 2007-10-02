""" This is a demo exposing all globals from the current process over
socket, to be accessible remotely.

run by:
pypy-c server.py

pypy-c needs to be compiled with --allworkingmodules in order to have socket
working.
"""

# things to export
# function
def f(x):
    return x + 3

# class
class X:
    def __init__(self):
        self.slot = 3
    
    def meth(self, f, arg):
        """ Method eating callable and calling it with an argument
        """
        assert callable(f)
        return f(arg)

# object
x = X()

# module
import sys

# constants
HOST = '127.0.0.1'
PORT = 12222

from distributed.socklayer import socket_loop
socket_loop((HOST, PORT), globals())
