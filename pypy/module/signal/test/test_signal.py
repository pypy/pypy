import os, py, sys
import signal as cpy_signal
from pypy.conftest import gettestobjspace


class TestCheckSignals:

    def setup_class(cls):
        if not hasattr(os, 'kill') or not hasattr(os, 'getpid'):
            py.test.skip("requires os.kill() and os.getpid()")
        cls.space = gettestobjspace(usemodules=['signal'])

    def test_checksignals(self):
        space = self.space
        w_received = space.appexec([], """():
            import signal
            received = []
            def myhandler(signum, frame):
                received.append(signum)
            signal.signal(signal.SIGUSR1, myhandler)
            return received""")
        #
        assert not space.is_true(w_received)
        #
        # send the signal now
        os.kill(os.getpid(), cpy_signal.SIGUSR1)
        #
        # myhandler() should not be immediately called
        assert not space.is_true(w_received)
        #
        # calling ec.checksignals() should call it
        space.getexecutioncontext().checksignals()
        assert space.is_true(w_received)


class AppTestSignal:

    def setup_class(cls):
        if not hasattr(os, 'kill') or not hasattr(os, 'getpid'):
            py.test.skip("requires os.kill() and os.getpid()")
        space = gettestobjspace(usemodules=['signal'])
        cls.space = space
        cls.w_signal = space.appexec([], "(): import signal; return signal")

    def test_exported_names(self):
        self.signal.__dict__   # crashes if the interpleveldefs are invalid

    def test_usr1(self):
        import types, posix
        signal = self.signal   # the signal module to test

        received = []
        def myhandler(signum, frame):
            assert isinstance(frame, types.FrameType)
            received.append(signum)
        signal.signal(signal.SIGUSR1, myhandler)

        posix.kill(posix.getpid(), signal.SIGUSR1)
        # the signal should be delivered to the handler immediately
        assert received == [signal.SIGUSR1]
        del received[:]

        posix.kill(posix.getpid(), signal.SIGUSR1)
        # the signal should be delivered to the handler immediately
        assert received == [signal.SIGUSR1]
        del received[:]

        signal.signal(signal.SIGUSR1, signal.SIG_IGN)

        posix.kill(posix.getpid(), signal.SIGUSR1)
        for i in range(10000):
            # wait a bit - signal should not arrive
            if received:
                break
        assert received == []

        signal.signal(signal.SIGUSR1, signal.SIG_DFL)


    def test_default_return(self):
        """
        Test that signal.signal returns SIG_DFL if that is the current handler.
        """
        from signal import signal, SIGUSR1, SIG_DFL, SIG_IGN

        try:
            for handler in SIG_DFL, SIG_IGN, lambda *a: None:
                signal(SIGUSR1, SIG_DFL)
                assert signal(SIGUSR1, handler) == SIG_DFL
        finally:
            signal(SIGUSR1, SIG_DFL)


    def test_ignore_return(self):
        """
        Test that signal.signal returns SIG_IGN if that is the current handler.
        """
        from signal import signal, SIGUSR1, SIG_DFL, SIG_IGN

        try:
            for handler in SIG_DFL, SIG_IGN, lambda *a: None:
                signal(SIGUSR1, SIG_IGN)
                assert signal(SIGUSR1, handler) == SIG_IGN
        finally:
            signal(SIGUSR1, SIG_DFL)


    def test_obj_return(self):
        """
        Test that signal.signal returns a Python object if one is the current
        handler.
        """
        from signal import signal, SIGUSR1, SIG_DFL, SIG_IGN
        def installed(*a):
            pass

        try:
            for handler in SIG_DFL, SIG_IGN, lambda *a: None:
                signal(SIGUSR1, installed)
                assert signal(SIGUSR1, handler) is installed
        finally:
            signal(SIGUSR1, SIG_DFL)


    def test_getsignal(self):
        """
        Test that signal.getsignal returns the currently installed handler.
        """
        from signal import getsignal, signal, SIGUSR1, SIG_DFL, SIG_IGN

        def handler(*a):
            pass

        try:
            assert getsignal(SIGUSR1) == SIG_DFL
            signal(SIGUSR1, SIG_DFL)
            assert getsignal(SIGUSR1) == SIG_DFL
            signal(SIGUSR1, SIG_IGN)
            assert getsignal(SIGUSR1) == SIG_IGN
            signal(SIGUSR1, handler)
            assert getsignal(SIGUSR1) is handler
        finally:
            signal(SIGUSR1, SIG_DFL)

        raises(ValueError, getsignal, 4444)
        raises(ValueError, signal, 4444, lambda *args: None)

    def test_alarm(self):
        from signal import alarm, signal, SIG_DFL, SIGALRM
        import time
        l = []
        def handler(*a):
            l.append(42)

        try:
            signal(SIGALRM, handler)
            alarm(1)
            time.sleep(2)
            assert l == [42]
            alarm(0)
            assert l == [42]
        finally:
            signal(SIGALRM, SIG_DFL)

    def test_set_wakeup_fd(self):
        import signal, posix, fcntl
        def myhandler(signum, frame):
            pass
        signal.signal(signal.SIGUSR1, myhandler)
        #
        def cannot_read():
            try:
                posix.read(fd_read, 1)
            except OSError:
                pass
            else:
                raise AssertionError, "os.read(fd_read, 1) succeeded?"
        #
        fd_read, fd_write = posix.pipe()
        flags = fcntl.fcntl(fd_write, fcntl.F_GETFL, 0)
        flags = flags | posix.O_NONBLOCK
        fcntl.fcntl(fd_write, fcntl.F_SETFL, flags)
        flags = fcntl.fcntl(fd_read, fcntl.F_GETFL, 0)
        flags = flags | posix.O_NONBLOCK
        fcntl.fcntl(fd_read, fcntl.F_SETFL, flags)
        #
        old_wakeup = signal.set_wakeup_fd(fd_write)
        try:
            cannot_read()
            posix.kill(posix.getpid(), signal.SIGUSR1)
            res = posix.read(fd_read, 1)
            assert res == '\x00'
            cannot_read()
        finally:
            old_wakeup = signal.set_wakeup_fd(old_wakeup)
        #
        signal.signal(signal.SIGUSR1, signal.SIG_DFL)

    def test_siginterrupt(self):
        import signal, os, time
        signum = signal.SIGUSR1
        def readpipe_is_not_interrupted():
            # from CPython's test_signal.readpipe_interrupted()
            r, w = os.pipe()
            ppid = os.getpid()
            pid = os.fork()
            if pid == 0:
                try:
                    time.sleep(1)
                    os.kill(ppid, signum)
                    time.sleep(1)
                finally:
                    os._exit(0)
            else:
                try:
                    os.close(w)
                    # we expect not to be interrupted.  If we are, the
                    # following line raises OSError(EINTR).
                    os.read(r, 1)
                finally:
                    os.waitpid(pid, 0)
                    os.close(r)
        #
        oldhandler = signal.signal(signum, lambda x,y: None)
        try:
            signal.siginterrupt(signum, 0)
            readpipe_is_not_interrupted()
            readpipe_is_not_interrupted()
        finally:
            signal.signal(signum, oldhandler)

class AppTestSignalSocket:

    def setup_class(cls):
        space = gettestobjspace(usemodules=['signal', '_socket'])
        cls.space = space

    def test_alarm_raise(self):
        try:
            from signal import alarm, signal, SIG_DFL, SIGALRM
        except ImportError:
            skip("no SIGALRM on this platform")
        import _socket
        class Alarm(Exception):
            pass
        def handler(*a):
            raise Alarm()

        s = _socket.socket()
        s.listen(1)
        try:
            signal(SIGALRM, handler)
            alarm(1)
            try:
                s.accept()
            except Alarm:
                pass
            else:
                raise Exception("should have raised Alarm")
            alarm(0)
        finally:
            signal(SIGALRM, SIG_DFL)

class AppTestItimer:
    spaceconfig = dict(usemodules=['signal'])

    def setup_class(cls):
        if sys.platform == 'win32':
            py.test.skip("Unix only")

    def test_itimer_real(self):
        import signal

        def sig_alrm(*args):
            self.called = True

        signal.signal(signal.SIGALRM, sig_alrm)
        old = signal.setitimer(signal.ITIMER_REAL, 1.0)
        assert old == (0, 0)

        val, interval = signal.getitimer(signal.ITIMER_REAL)
        assert val <= 1.0
        assert interval == 0.0

        signal.pause()
        assert self.called

    def test_itimer_exc(self):
        import signal

        raises(signal.ItimerError, signal.setitimer, -1, 0)
