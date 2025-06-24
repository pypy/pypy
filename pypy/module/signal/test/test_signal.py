import os, pytest, sys
import signal as cpy_signal


class TestCheckSignals:
    spaceconfig = dict(usemodules=['signal'])

    def setup_class(cls):
        if not hasattr(os, 'kill') or not hasattr(os, 'getpid'):
            pytest.skip("requires os.kill() and os.getpid()")
        if not hasattr(cpy_signal, 'SIGUSR1'):
            pytest.skip("requires SIGUSR1 in signal")

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
        print(space.getexecutioncontext().checksignals)
        space.getexecutioncontext().checksignals()
        assert space.is_true(w_received)


class AppTestSignal:
    spaceconfig = {
        "usemodules": ['signal', 'time'] + (['fcntl'] if os.name != 'nt' else []),
    }

    def setup_class(cls):
        cls.w_signal = cls.space.getbuiltinmodule('signal')
        cls.w_temppath = cls.space.wrap(
            str(pytest.ensuretemp("signal").join("foo.txt")))

    def test_exported_names(self):
        import os
        self.signal.__dict__   # crashes if the interpleveldefs are invalid
        if os.name == 'nt':
            assert self.signal.CTRL_BREAK_EVENT == 1
            assert self.signal.CTRL_C_EVENT == 0

    def test_basics(self):
        import types, os
        if not hasattr(os, 'kill') or not hasattr(os, 'getpid'):
            skip("requires os.kill() and os.getpid()")
        signal = self.signal   # the signal module to test
        if not hasattr(signal, 'SIGUSR1'):
            skip("requires SIGUSR1 in signal")
        signum = signal.SIGUSR1

        received = []
        def myhandler(signum, frame):
            assert isinstance(frame, types.FrameType)
            received.append(signum)
        signal.signal(signum, myhandler)

        os.kill(os.getpid(), signum)
        # the signal should be delivered to the handler immediately
        assert received == [signum]
        del received[:]

        os.kill(os.getpid(), signum)
        # the signal should be delivered to the handler immediately
        assert received == [signum]
        del received[:]

        signal.signal(signum, signal.SIG_IGN)

        os.kill(os.getpid(), signum)
        for i in range(10000):
            # wait a bit - signal should not arrive
            if received:
                break
        assert received == []

        signal.signal(signum, signal.SIG_DFL)

    def test_default_return(self):
        """
        Test that signal.signal returns SIG_DFL if that is the current handler.
        """
        from signal import signal, SIGINT, SIG_DFL, SIG_IGN

        try:
            for handler in SIG_DFL, SIG_IGN, lambda *a: None:
                signal(SIGINT, SIG_DFL)
                assert signal(SIGINT, handler) == SIG_DFL
        finally:
            signal(SIGINT, SIG_DFL)

    def test_ignore_return(self):
        """
        Test that signal.signal returns SIG_IGN if that is the current handler.
        """
        from signal import signal, SIGINT, SIG_DFL, SIG_IGN

        try:
            for handler in SIG_DFL, SIG_IGN, lambda *a: None:
                signal(SIGINT, SIG_IGN)
                assert signal(SIGINT, handler) == SIG_IGN
        finally:
            signal(SIGINT, SIG_DFL)

    def test_obj_return(self):
        """
        Test that signal.signal returns a Python object if one is the current
        handler.
        """
        from signal import signal, SIGINT, SIG_DFL, SIG_IGN
        def installed(*a):
            pass

        try:
            for handler in SIG_DFL, SIG_IGN, lambda *a: None:
                signal(SIGINT, installed)
                assert signal(SIGINT, handler) is installed
        finally:
            signal(SIGINT, SIG_DFL)

    def test_getsignal(self):
        """
        Test that signal.getsignal returns the currently installed handler.
        """
        from signal import getsignal, signal, SIGINT, SIG_DFL, SIG_IGN

        def handler(*a):
            pass

        try:
            assert getsignal(SIGINT) == SIG_DFL
            signal(SIGINT, SIG_DFL)
            assert getsignal(SIGINT) == SIG_DFL
            signal(SIGINT, SIG_IGN)
            assert getsignal(SIGINT) == SIG_IGN
            signal(SIGINT, handler)
            assert getsignal(SIGINT) is handler
        finally:
            signal(SIGINT, SIG_DFL)

    def test_check_signum(self):
        import sys
        from signal import getsignal, signal, NSIG

        # signum out of range fails
        raises(ValueError, getsignal, NSIG)
        raises(ValueError, signal, NSIG, lambda *args: None)

        # on windows invalid signal within range should pass getsignal but fail signal
        if sys.platform == 'win32':
            assert getsignal(7) == None
            raises(ValueError, signal, 7, lambda *args: None)

    def test_alarm(self):
        try:
            from signal import alarm, signal, SIG_DFL, SIGALRM
        except:
            skip('no alarm on this platform')
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
        try:
            import signal, posix, fcntl
        except ImportError:
            skip('cannot import posix or fcntl')
        def myhandler(signum, frame):
            pass
        signal.signal(signal.SIGINT, myhandler)
        #
        def cannot_read():
            try:
                posix.read(fd_read, 1)
            except OSError:
                pass
            else:
                raise AssertionError("os.read(fd_read, 1) succeeded?")
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
            posix.kill(posix.getpid(), signal.SIGINT)
            res = posix.read(fd_read, 1)
            assert res == '\x00'
            cannot_read()
        finally:
            old_wakeup = signal.set_wakeup_fd(old_wakeup)
        #
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    def test_set_wakeup_fd_invalid(self):
        import signal
        with open(self.temppath, 'wb') as f:
            fd = f.fileno()
        raises(ValueError, signal.set_wakeup_fd, fd)

    def test_siginterrupt(self):
        import signal, os, time
        if not hasattr(signal, 'siginterrupt'):
            skip('non siginterrupt in signal')
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

    def test_default_int_handler(self):
        import signal
        for args in [(), (1, 2)]:
            try:
                signal.default_int_handler(*args)
            except KeyboardInterrupt:
                pass
            else:
                raise AssertionError("did not raise!")


class AppTestSignalSocket:
    spaceconfig = dict(usemodules=['signal', '_socket'])

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
            pytest.skip("Unix only")

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


class AppTestRemotelyTriggeredDebugger:
    spaceconfig = {
        "usemodules": ['signal', 'time'] + (['fcntl'] if os.name != 'nt' else []),
    }

    def setup_class(cls):
        from pypy.interpreter.gateway import interp2app
        from rpython.rlib.rsignal import pypysig_getaddr_occurred_fullstruct
        if cls.runappdirect:
            pytest.skip("can only be run untranslated")
        cls.w_signal = cls.space.getbuiltinmodule('signal')
        tmpdir = pytest.ensuretemp("signal")
        outfile = tmpdir.join('out.txt')
        tmpfile = tmpdir.join("debugger.py")
        tmpfile.write('''
with open(%r, 'w') as f:
    f.write('done')
print('done')
''' % str(outfile))
        cls.w_outfile = cls.space.wrap(
            str(outfile))
        def trigger_debugger(space):
            addr = pypysig_getaddr_occurred_fullstruct()
            for index, c in enumerate(str(tmpfile)):
                addr.c_debugger_script_path[index] = c
            addr.c_debugger_script_path[index + 1] = '\x00'
            addr.c_debugger_pending_call = 1
            addr.c_value = -1
        cls.w_trigger_debugger = cls.space.wrap(interp2app(trigger_debugger))

    def test_run_debugger(self):
        self.trigger_debugger() # should happen right away
        with open(self.outfile) as f:
            content = f.read()
            assert content == 'done'

    def test_disable_debugger(self):
        import __pypy__
        with open(self.outfile, 'w') as f:
            f.write('nothing')
        assert __pypy__._pypy_disable_remote_debugger == False
        __pypy__._pypy_disable_remote_debugger = True
        try:
            self.trigger_debugger() # should happen right away
        finally:
            __pypy__._pypy_disable_remote_debugger = False
        with open(self.outfile) as f:
            content = f.read()
            assert content == 'nothing'
