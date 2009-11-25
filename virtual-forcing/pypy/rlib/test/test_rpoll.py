import thread
from pypy.rlib.rsocket import *
from pypy.rlib.rpoll import *
from pypy.rpython.test.test_llinterp import interpret

def setup_module(mod):
    rsocket_startup()

def test_simple():
    serv = RSocket(AF_INET, SOCK_STREAM)
    serv.bind(INETAddress('127.0.0.1', INADDR_ANY))
    serv.listen(1)
    servaddr = serv.getsockname()

    events = poll({serv.fileno(): POLLIN}, timeout=100)
    assert len(events) == 0

    cli = RSocket(AF_INET, SOCK_STREAM)
    cli.setblocking(False)
    err = cli.connect_ex(servaddr)
    assert err != 0

    events = poll({serv.fileno(): POLLIN}, timeout=500)
    assert len(events) == 1
    assert events[0][0] == serv.fileno()
    assert events[0][1] & POLLIN

    servconn, cliaddr = serv.accept()

    events = poll({serv.fileno(): POLLIN,
                   cli.fileno(): POLLOUT}, timeout=500)
    assert len(events) == 1
    assert events[0][0] == cli.fileno()
    assert events[0][1] & POLLOUT

    err = cli.connect_ex(servaddr)
    # win32 oddity: returns WSAEISCONN when the connection finally succeed.
    assert err == 0 or err == 10056

    events = poll({servconn.fileno(): POLLIN,
                   cli.fileno(): POLLIN}, timeout=100)
    assert len(events) == 0

    events = poll({servconn.fileno(): POLLOUT,
                   cli.fileno(): POLLOUT}, timeout=100)
    assert len(events) >= 1

    cli.close()
    servconn.close()
    serv.close()

def test_select():
    def f():
        readend, writeend = os.pipe()
        try:
            iwtd, owtd, ewtd = select([readend], [], [], 0.0)
            assert iwtd == owtd == ewtd == []
            os.write(writeend, 'X')
            iwtd, owtd, ewtd = select([readend], [], [])
            assert iwtd == [readend]
            assert owtd == ewtd == []

        finally:
            os.close(readend)
            os.close(writeend)
    f()
    interpret(f, [])

def test_select_timeout():
    from time import time
    def f():
        # once there was a bug where the sleeping time was doubled
        a = time()
        iwtd, owtd, ewtd = select([], [], [], 5.0)
        diff = time() - a
        assert 4.8 < diff < 9.0
    interpret(f, [])


def test_translate():
    from pypy.translator.c.test.test_genc import compile

    def func():
        poll({})

    compile(func, [])
