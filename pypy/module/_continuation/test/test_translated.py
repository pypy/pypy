import py
try:
    import _continuation
except ImportError:
    py.test.skip("to run on top of a translated pypy-c")

import sys, random

# ____________________________________________________________

STATUS_MAX = 50000
CONTINULETS = 50

def set_fast_mode():
    global STATUS_MAX, CONTINULETS
    STATUS_MAX = 100
    CONTINULETS = 5

# ____________________________________________________________

class Done(Exception):
    pass


class Runner(object):

    def __init__(self):
        self.foobar = 12345
        self.conts = {}     # {continulet: parent-or-None}
        self.contlist = []

    def run_test(self):
        self.start_continulets()
        self.n = 0
        try:
            while True:
                self.do_switch(src=None)
                assert self.target is None
        except Done:
            self.check_traceback(sys.exc_info()[2])

    def do_switch(self, src):
        assert src not in self.conts.values()
        c = random.choice(self.contlist)
        self.target = self.conts[c]
        self.conts[c] = src
        c.switch()
        assert self.target is src

    def run_continulet(self, c, i):
        while True:
            assert self.target is c
            assert self.contlist[i] is c
            self.do_switch(c)
            assert self.foobar == 12345
            self.n += 1
            if self.n >= STATUS_MAX:
                raise Done

    def start_continulets(self, i=0):
        c = _continuation.continulet(self.run_continulet, i)
        self.contlist.append(c)
        if i < CONTINULETS:
            self.start_continulets(i + 1)
            # ^^^ start each continulet with a different base stack
        self.conts[c] = c   # initially (i.e. not started) there are all loops

    def check_traceback(self, tb):
        found = []
        tb = tb.tb_next
        while tb:
            if tb.tb_frame.f_code.co_name != 'do_switch':
                assert tb.tb_frame.f_code.co_name == 'run_continulet', (
                    "got %r" % (tb.tb_frame.f_code.co_name,))
                found.append(tb.tb_frame.f_locals['c'])
            tb = tb.tb_next
        found.reverse()
        #
        expected = []
        c = self.target
        while c is not None:
            expected.append(c)
            c = self.conts[c]
        #
        assert found == expected, "%r == %r" % (found, expected)

# ____________________________________________________________

class AppTestWrapper:
    def setup_class(cls):
        "Run test_various_depths() when we are run with 'pypy py.test -A'."
        from pypy.conftest import option
        if not option.runappdirect:
            py.test.skip("meant only for -A run")

    def test_single_threaded(self):
        for i in range(20):
            yield Runner().run_test,

    def test_multi_threaded(self):
        for i in range(5):
            yield multithreaded_test,

class ThreadTest(object):
    def __init__(self, lock):
        self.lock = lock
        self.ok = False
        lock.acquire()
    def run(self):
        try:
            Runner().run_test()
            self.ok = True
        finally:
            self.lock.release()

def multithreaded_test():
    try:
        import thread
    except ImportError:
        py.test.skip("no threads")
    ts = [ThreadTest(thread.allocate_lock()) for i in range(5)]
    for t in ts:
        thread.start_new_thread(t.run, ())
    for t in ts:
        t.lock.acquire()
    for t in ts:
        assert t.ok

# ____________________________________________________________

if __name__ == '__main__':
    Runner().run_test()
