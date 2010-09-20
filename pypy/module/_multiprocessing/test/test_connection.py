import py
import sys
from pypy.conftest import gettestobjspace

class TestConnection:
    def test_simple(self):
        from pypy.module._multiprocessing import interp_connection

class AppTestConnection:
    def setup_class(cls):
        if sys.platform != "win32":
            py.test.skip("win32 only")
        cls.space = gettestobjspace(usemodules=('_multiprocessing', 'thread'))
        if sys.platform == "win32":
            # stubs for some modules,
            # just for multiprocessing to import correctly.
            space = cls.space
            w_modules = space.sys.get('modules')
            space.setitem(w_modules, space.wrap('msvcrt'), space.sys)
            space.setitem(w_modules, space.wrap('_subprocess'), space.sys)

    def test_pipe_connection(self):
        import multiprocessing
        obj = [1, 2.0, "hello"]
        whandle, rhandle = multiprocessing.Pipe()
        whandle.send(obj)
        obj2 = rhandle.recv()
        assert obj == obj2


