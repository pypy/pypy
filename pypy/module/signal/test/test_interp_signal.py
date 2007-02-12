import os, py
from pypy import conftest; conftest.translation_test_so_skip_if_appdirect()
from pypy.translator.c.test.test_genc import compile
from pypy.module.signal import interp_signal

def setup_module(mod):
    if not hasattr(os, 'kill') or not hasattr(os, 'getpid'):
        py.test.skip("requires os.kill() and os.getpid()")


def check(expected):
    res = interp_signal.pypysig_poll()
    os.write(1, "poll() => %d, expected %d\n" % (res, expected))
    assert res == expected

def test_simple():
    import os
    check(-1)
    check(-1)
    for i in range(3):
        interp_signal.pypysig_setflag(interp_signal.SIGUSR1)
        os.kill(os.getpid(), interp_signal.SIGUSR1)
        check(interp_signal.SIGUSR1)
        check(-1)
        check(-1)

    interp_signal.pypysig_ignore(interp_signal.SIGUSR1)
    os.kill(os.getpid(), interp_signal.SIGUSR1)
    check(-1)
    check(-1)

    interp_signal.pypysig_default(interp_signal.SIGUSR1)
    check(-1)


def test_compile():
    fn = compile(test_simple, [])
    fn()
