from pypy.conftest import gettestobjspace

class AppTestSignal:

    def setup_class(cls):
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
