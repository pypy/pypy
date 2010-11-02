import py
import sys
from pypy.conftest import gettestobjspace, option
from pypy.interpreter.gateway import interp2app

class TestImport:
    def test_simple(self):
        from pypy.module._multiprocessing import interp_connection
        from pypy.module._multiprocessing import interp_semaphore

class AppTestBufferTooShort:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_multiprocessing', 'thread'))
        cls.space = space

        if option.runappdirect:
            def raiseBufferTooShort(data):
                import multiprocessing
                raise multiprocessing.BufferTooShort(data)
            cls.w_raiseBufferTooShort = raiseBufferTooShort
        else:
            from pypy.module._multiprocessing import interp_connection
            def raiseBufferTooShort(space, w_data):
                raise interp_connection.BufferTooShort(space, w_data)
            cls.w_raiseBufferTooShort = space.wrap(
                interp2app(raiseBufferTooShort))

    def test_exception(self):
        import multiprocessing
        try:
            self.raiseBufferTooShort("data")
        except multiprocessing.BufferTooShort, e:
            assert isinstance(e, multiprocessing.ProcessError)
            assert e.args == ("data",)

class BaseConnectionTest(object):
    def test_connection(self):
        rhandle, whandle = self.make_pair()

        obj = [1, 2.0, "hello"]
        whandle.send(obj)
        obj2 = rhandle.recv()
        assert obj == obj2

    def test_poll(self):
        rhandle, whandle = self.make_pair()

        assert rhandle.poll() == False
        assert rhandle.poll(1) == False
        whandle.send(1)
        assert rhandle.poll() == True
        assert rhandle.poll(None) == True
        assert rhandle.recv() == 1
        assert rhandle.poll() == False

class AppTestWinpipeConnection(BaseConnectionTest):
    def setup_class(cls):
        if sys.platform != "win32":
            py.test.skip("win32 only")

        if not option.runappdirect:
            space = gettestobjspace(usemodules=('_multiprocessing', 'thread'))
            cls.space = space

            # stubs for some modules,
            # just for multiprocessing to import correctly on Windows
            w_modules = space.sys.get('modules')
            space.setitem(w_modules, space.wrap('msvcrt'), space.sys)
            space.setitem(w_modules, space.wrap('_subprocess'), space.sys)
        else:
            import _multiprocessing

        cls.w_make_pair = cls.space.appexec([], """():
            import multiprocessing
            def make_pair():
                rhandle, whandle = multiprocessing.Pipe()
                return rhandle, whandle
            return make_pair
        """)

class AppTestSocketConnection(BaseConnectionTest):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_multiprocessing', 'thread'))
        cls.space = space
        cls.w_make_pair = space.appexec([], """():
            import _multiprocessing
            import os
            def make_pair():
                fd1, fd2 = os.pipe()
                rhandle = _multiprocessing.Connection(fd1, writable=False)
                whandle = _multiprocessing.Connection(fd2, readable=False)
                return rhandle, whandle
            return make_pair
        """)

    if sys.platform == "win32":
        def test_poll(self):
            skip("poll() does not accept file handles on Windows")
