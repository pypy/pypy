import py
import sys
from pypy.conftest import gettestobjspace, option
from pypy.interpreter.gateway import interp2app, W_Root

class TestImport:
    def test_simple(self):
        from pypy.module._multiprocessing import interp_connection
        from pypy.module._multiprocessing import interp_semaphore

class AppTestBufferTooShort:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_multiprocessing', 'thread', 'signal'))
        cls.space = space

        if option.runappdirect:
            def raiseBufferTooShort(self, data):
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
        raises(IOError, whandle.poll)

    def test_read_into(self):
        import array, multiprocessing
        rhandle, whandle = self.make_pair()

        obj = [1, 2.0, "hello"]
        whandle.send(obj)
        buffer = array.array('b', [0]*10)
        raises(multiprocessing.BufferTooShort, rhandle.recv_bytes_into, buffer)
        assert rhandle.readable

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

    def w_make_pair(self):
        import multiprocessing

        return multiprocessing.Pipe(duplex=False)

class AppTestSocketConnection(BaseConnectionTest):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_multiprocessing', 'thread', 'signal'))
        cls.space = space
        cls.w_connections = space.newlist([])

        def socketpair(space):
            "A socket.socketpair() that works on Windows"
            import socket, errno
            serverSocket = socket.socket()
            serverSocket.bind(('127.0.0.1', 0))
            serverSocket.listen(1)

            client = socket.socket()
            client.setblocking(False)
            try:
                client.connect(('127.0.0.1', serverSocket.getsockname()[1]))
            except socket.error, e:
                assert e.args[0] in (errno.EINPROGRESS, errno.EWOULDBLOCK)
            server, addr = serverSocket.accept()

            # keep sockets alive during the test
            space.call_method(cls.w_connections, "append", space.wrap(server))
            space.call_method(cls.w_connections, "append", space.wrap(client))

            return space.wrap((server.fileno(), client.fileno()))
        if option.runappdirect:
            cls.w_socketpair = lambda self: socketpair(space)
        else:
            cls.w_socketpair = space.wrap(interp2app(socketpair))

    def w_make_pair(self):
        import _multiprocessing
        import os

        fd1, fd2 = self.socketpair()
        rhandle = _multiprocessing.Connection(fd1, writable=False)
        whandle = _multiprocessing.Connection(fd2, readable=False)
        self.connections.append(rhandle)
        self.connections.append(whandle)
        return rhandle, whandle

    def teardown_method(self, func):
        # Work hard to close all sockets and connections now!
        # since the fd is probably already closed, another unrelated
        # part of the program will probably reuse it;
        # And any object forgotten here will close it on destruction...
        try:
            w_connections = self.w_connections
        except AttributeError:
            return
        space = self.space
        for c in space.unpackiterable(w_connections):
            if isinstance(c, W_Root):
                space.call_method(c, "close")
            else:
                c.close()
        space.delslice(w_connections, space.wrap(0), space.wrap(100))
