import autopath
import py
import os.path, subprocess, sys, thread
import _socket
from pypy.translator.c.test.test_genc import compile
from pypy.translator.translator import Translator

HOST = "localhost"
PORT = 8037

def setup_module(mod):
    import pypy.module._socket.rpython.exttable   # for declare()/declaretype()
    from pypy.module._socket.test import echoserver
    thread.start_new_thread(echoserver.start_server, ())

def teardown_module(mod):
    import telnetlib
    tn = telnetlib.Telnet(HOST, PORT)
    tn.write("shutdown\n")
    tn.close()
    del tn

def test_connect():
    import os
    from pypy.module._socket.rpython import rsocket
    def does_stuff():
        fd = rsocket.newsocket(_socket.AF_INET, _socket.SOCK_STREAM, 0)
        rsocket.connect(fd, (HOST, PORT, 0, 0))
        sockname = rsocket.getpeername(fd)
        os.close(fd)
        return sockname[1]
    f1 = compile(does_stuff, [])
    res = f1()
    assert res == PORT
