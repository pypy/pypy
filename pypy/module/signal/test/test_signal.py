import os, py
from pypy.conftest import gettestobjspace

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
        for i in range(10000):
             # wait a bit for the signal to be delivered to the handler
            if received:
                break
        assert received == [signal.SIGUSR1]
        del received[:]

        posix.kill(posix.getpid(), signal.SIGUSR1)
        for i in range(10000):
             # wait a bit for the signal to be delivered to the handler
            if received:
                break
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
