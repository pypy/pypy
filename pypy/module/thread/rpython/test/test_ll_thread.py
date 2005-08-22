import thread
import pypy.module.thread.rpython.exttable   # for declare()/declaretype()
from pypy.module.thread.rpython.ll_thread import *
from pypy.translator.annrpython import RPythonAnnotator
from pypy.rpython.test.test_llinterp import interpret


def test_annotate_lock():
    def fn():
        return thread.allocate_lock().acquire(False)
    a = RPythonAnnotator()
    s = a.build_types(fn, [])
    # result should be a boolean
    assert s.knowntype == bool

def test_lock():
    def fn():
        l = thread.allocate_lock()
        ok1 = l.acquire(True)
        ok2 = l.acquire(False)
        l.release()
        ok3 = l.acquire(False)
        return ok1 and not ok2 and ok3
    res = interpret(fn, [])
    assert res is True

def test_thread_error():
    def fn():
        l = thread.allocate_lock()
        try:
            l.release()
        except thread.error:
            return True
        else:
            return False
    res = interpret(fn, [])
    assert res is True
