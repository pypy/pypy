from pypy.module.thread.test.support import GenericTestThread


class AppTestLocal(GenericTestThread):

    def test_local_1(self):
        import thread
        from thread import _local as tlsobject
        freed = []
        class X:
            def __del__(self):
                freed.append(1)

        ok = []
        TLS1 = tlsobject()
        TLS2 = tlsobject()
        TLS1.aa = "hello"
        def f(i):
            success = False
            try:
                a = TLS1.aa = i
                b = TLS1.bbb = X()
                c = TLS2.cccc = i*3
                d = TLS2.ddddd = X()
                self.busywait(0.05)
                assert TLS1.aa == a
                assert TLS1.bbb is b
                assert TLS2.cccc == c
                assert TLS2.ddddd is d
                success = True
            finally:
                ok.append(success)
        for i in range(20):
            thread.start_new_thread(f, (i,))
        self.waitfor(lambda: len(ok) == 20, delay=3)
        assert ok == 20*[True] # see stdout/stderr for failures in the threads

        self.waitfor(lambda: len(freed) >= 40)
        assert len(freed) == 40
        #  in theory, all X objects should have been freed by now.  Note that
        #  Python's own thread._local objects suffer from the very same "bug" that
        #  tls.py showed originally, and leaves len(freed)==38: the last thread's
        #  __dict__ remains stored in the TLS1/TLS2 instances, although it is not
        #  really accessible any more.

        assert TLS1.aa == "hello"


    def test_local_init(self):
        import thread
        tags = [1, 2, 3, 4, 5, 54321]
        seen = []

        raises(TypeError, thread._local, a=1)
        raises(TypeError, thread._local, 1)

        class X(thread._local):
            def __init__(self, n):
                assert n == 42
                self.tag = tags.pop()

        x = X(42)
        assert x.tag == 54321
        def f():
            seen.append(x.tag)
        for i in range(5):
            thread.start_new_thread(f, ())
        self.waitfor(lambda: len(seen) == 5, delay=2)
        seen1 = seen[:]
        seen1.sort()
        assert seen1 == [1, 2, 3, 4, 5]
        assert tags == []

    def test_local_setdict(self):
        import thread
        x = thread._local()
        # XXX: On Cpython these are AttributeErrors
        raises(TypeError, "x.__dict__ = 42")
        raises(TypeError, "x.__dict__ = {}")

        done = []
        def f(n):
            x.spam = n
            assert x.__dict__["spam"] == n
            done.append(1)
        for i in range(5):
            thread.start_new_thread(f, (i,))
        self.waitfor(lambda: len(done) == 5, delay=2)
        assert len(done) == 5
