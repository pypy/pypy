import sys


class AppTestMinimal:
    spaceconfig = dict(usemodules=['__pypy__'])

    def test_signal(self):
        from __pypy__ import thread
        with thread.signals_enabled:
            pass
        # assert did not crash


class AppTestThreadSignal:
    spaceconfig = dict(usemodules=['__pypy__', 'thread', 'signal', 'time'])

    def test_enable_signals(self):
        import __pypy__, thread, signal, time

        def subthread():
            try:
                with __pypy__.thread.signals_enabled:
                    thread.interrupt_main()
                    for i in range(10):
                        print 'x'
                        time.sleep(0.1)
            except BaseException, e:
                interrupted.append(e)
            finally:
                done.append(None)

        # This is normally called by app_main.py
        signal.signal(signal.SIGINT, signal.default_int_handler)

        for i in range(10):
            __pypy__.thread._signals_exit()
            try:
                done = []
                interrupted = []
                thread.start_new_thread(subthread, ())
                for i in range(10):
                    if len(done): break
                    print '.'
                    time.sleep(0.1)
                assert len(done) == 1
                assert len(interrupted) == 1
                assert 'KeyboardInterrupt' in interrupted[0].__class__.__name__
            finally:
                __pypy__.thread._signals_enter()


class AppTestThreadSignalLock:
    spaceconfig = dict(usemodules=['__pypy__', 'thread', 'signal'])

    def setup_class(cls):
        if (not cls.runappdirect or
                '__pypy__' not in sys.builtin_module_names):
            import py
            py.test.skip("this is only a test for -A runs on top of pypy")

    def test_enable_signals(self):
        import __pypy__, thread, signal, time

        interrupted = []
        lock = thread.allocate_lock()
        lock.acquire()

        def subthread():
            try:
                time.sleep(0.25)
                with __pypy__.thread.signals_enabled:
                    thread.interrupt_main()
            except BaseException, e:
                interrupted.append(e)
            finally:
                lock.release()

        thread.start_new_thread(subthread, ())
        lock.acquire()
        assert len(interrupted) == 1
        assert 'KeyboardInterrupt' in interrupted[0].__class__.__name__
