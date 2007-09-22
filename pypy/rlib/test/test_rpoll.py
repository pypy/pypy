import thread
from pypy.rlib.rsocket import *
from pypy.rlib.rpoll import *

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
    assert err == 0

    events = poll({servconn.fileno(): POLLIN,
                   cli.fileno(): POLLIN}, timeout=100)
    assert len(events) == 0

    events = poll({servconn.fileno(): POLLOUT,
                   cli.fileno(): POLLOUT}, timeout=100)
    assert len(events) >= 1

    cli.close()
    servconn.close()
    serv.close()
