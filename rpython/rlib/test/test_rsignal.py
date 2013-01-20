import os, py
from rpython.translator.c.test.test_genc import compile
from rpython.rlib import rsignal

def setup_module(mod):
    if not hasattr(os, 'kill') or not hasattr(os, 'getpid'):
        py.test.skip("requires os.kill() and os.getpid()")
    if not hasattr(rsignal, 'SIGUSR1'):
        py.test.skip("requires SIGUSR1 in signal")


def check(expected):
    res = rsignal.pypysig_poll()
    os.write(1, "poll() => %d, expected %d\n" % (res, expected))
    assert res == expected

def test_simple():
    import os
    check(-1)
    check(-1)
    for i in range(3):
        rsignal.pypysig_setflag(rsignal.SIGUSR1)
        os.kill(os.getpid(), rsignal.SIGUSR1)
        check(rsignal.SIGUSR1)
        check(-1)
        check(-1)

    rsignal.pypysig_ignore(rsignal.SIGUSR1)
    os.kill(os.getpid(), rsignal.SIGUSR1)
    check(-1)
    check(-1)

    rsignal.pypysig_default(rsignal.SIGUSR1)
    check(-1)


def test_compile():
    fn = compile(test_simple, [])
    fn()
