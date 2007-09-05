from pypy.module.thread.test.support import GenericTestThread

class AppTestThread(GenericTestThread):

    def test_start_new_thread(self):
        import thread
        feedback = []
        please_start = []
        def f(x, y, z):
            self.waitfor(lambda: please_start)
            feedback.append(42)
        thread.start_new_thread(f, (1, 2), {'z': 3})
        assert feedback == []   # still empty
        please_start.append(1)  # trigger
        self.waitfor(lambda: feedback)
        assert feedback == [42]

    def test_start_new_thread_args(self):
        import thread
        def f():
            pass
        test_args = [
            (f, [], {}),
            (f, (), []),
            ("", (), {}),
        ]
        for args in test_args:
            try:
                thread.start_new_thread(*args)
                assert False
            except TypeError:
                pass

    def test_get_ident(self):
        import thread
        ident = thread.get_ident()
        feedback = []
        def f():
            feedback.append(thread.get_ident())
        ident2 = thread.start_new_thread(f, ())
        assert ident2 != ident
        assert ident == thread.get_ident()
        self.waitfor(lambda: feedback)
        assert feedback == [ident2]

    def test_sys_getframe(self):
        # this checks that each thread gets its own ExecutionContext.
        def main():
            import thread, sys
            def dump_frames(feedback):
                f = sys._getframe()
                for i in range(3):
                    if f is None:
                        feedback.append(None)
                    else:
                        feedback.append(f.f_code.co_name)
                        self.busywait(0.04)
                        assert f is sys._getframe(i)
                        f = f.f_back
            def dummyfn(feedback):
                dump_frames(feedback)
            feedback = []
            dummyfn(feedback)
            assert feedback == ['dump_frames', 'dummyfn', 'main']
            feedbacks = []
            for i in range(3):
                feedback = []
                thread.start_new_thread(dummyfn, (feedback,))
                feedbacks.append(feedback)
            expected = 3*[['dump_frames', 'dummyfn', None]]   # without 'main'
            self.waitfor(lambda: feedbacks == expected)
            assert feedbacks == expected
        main()

    def test_thread_exit(self):
        import thread, sys, StringIO
        def fn1():
            thread.exit()
        def fn2():
            raise SystemExit
        def fn3():
            raise ValueError("hello world")
        prev = sys.stderr
        try:
            sys.stderr = StringIO.StringIO()
            thread.start_new_thread(fn1, ())
            thread.start_new_thread(fn2, ())
            self.busywait(0.2)   # time for the threads to finish
            assert sys.stderr.getvalue() == ''

            sys.stderr = StringIO.StringIO()
            thread.start_new_thread(fn3, ())
            self.waitfor(lambda: "ValueError" in sys.stderr.getvalue())
            result = sys.stderr.getvalue()
            assert "ValueError" in result
            assert "hello world" in result
        finally:
            sys.stderr = prev

    def test_perthread_excinfo(self):
        import thread, sys
        done = []
        def fn1(n):
            success = False
            try:
                caught = False
                try:
                    try:
                        {}[n]
                    except KeyError:
                        self.busywait(0.05)
                        caught = True
                        raise
                except KeyError:
                    self.busywait(0.05)
                    assert caught
                    etype, evalue, etb = sys.exc_info()
                    assert etype is KeyError
                    assert evalue.args[0] == n
                    success = True
            finally:
                done.append(success)
        for i in range(20):
            thread.start_new_thread(fn1, (i,))
        self.waitfor(lambda: len(done) == 20)
        assert done == 20*[True]  # see stderr for failures in the threads

    def test_no_corruption(self):
        import thread
        lst = []
        done_marker = []
        def f(x, done):
            for j in range(40):
                lst.insert(0, x+j)  # all threads trying to modify the same list
            done.append(True)
        for i in range(0, 120, 40):
            done = []
            thread.start_new_thread(f, (i, done))
            done_marker.append(done)
        for done in done_marker:
            self.waitfor(lambda: done, delay=3)
            assert done    # see stderr for failures in threads
        assert sorted(lst) == range(120)
