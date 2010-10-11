import py
import sys
from pypy.conftest import gettestobjspace

class TestImport:
    def test_simple(self):
        from pypy.module._multiprocessing import interp_connection
        from pypy.module._multiprocessing import interp_semaphore

class AppTestConnection:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_multiprocessing', 'thread'))
        cls.space = space
        if sys.platform == "win32":
            # stubs for some modules,
            # just for multiprocessing to import correctly.
            w_modules = space.sys.get('modules')
            space.setitem(w_modules, space.wrap('msvcrt'), space.sys)
            space.setitem(w_modules, space.wrap('_subprocess'), space.sys)

        # import multiprocessing once
        space.appexec([], """(): import multiprocessing""")

    def test_winpipe_connection(self):
        import sys
        if sys.platform != "win32":
            skip("win32 only")

        import multiprocessing
        rhandle, whandle = multiprocessing.Pipe()

        obj = [1, 2.0, "hello"]
        whandle.send(obj)
        obj2 = rhandle.recv()
        assert obj == obj2

    def test_ospipe_connection(self):
        import _multiprocessing
        import os
        fd1, fd2 = os.pipe()
        rhandle = _multiprocessing.Connection(fd1, writable=False)
        whandle = _multiprocessing.Connection(fd2, readable=False)

        obj = [1, 2.0, "hello"]
        whandle.send(obj)
        obj2 = rhandle.recv()
        assert obj == obj2


