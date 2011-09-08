import py

from pypy.conftest import gettestobjspace


class AppTestEpoll(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=["select", "_socket", "posix"])

        import errno
        import select

        if not hasattr(select, "epoll"):
            py.test.skip("test requires linux 2.6")
        try:
            select.epoll()
        except IOError, e:
            if e.errno == errno.ENOSYS:
                py.test.skip("kernel doesn't support epoll()")

    def setup_method(self, meth):
        self.w_sockets = self.space.wrap([])

    def teardown_method(self, meth):
        for socket in self.space.unpackiterable(self.w_sockets):
            self.space.call_method(socket, "close")

    def w_socket_pair(self):
        import socket

        server_socket = socket.socket()
        server_socket.bind(('127.0.0.1', 0))
        server_socket.listen(1)
        client = socket.socket()
        client.setblocking(False)
        raises(socket.error,
            client.connect, ('127.0.0.1', server_socket.getsockname()[1])
        )
        server, addr = server_socket.accept()

        self.sockets.extend([server_socket, client, server])
        return client, server

    def test_create(self):
        import select

        ep = select.epoll(16)
        assert ep.fileno() > 0
        assert not ep.closed
        ep.close()
        assert ep.closed
        raises(ValueError, ep.fileno)

    def test_badcreate(self):
        import select

        raises(TypeError, select.epoll, 1, 2, 3)
        raises(TypeError, select.epoll, 'foo')
        raises(TypeError, select.epoll, None)
        raises(TypeError, select.epoll, ())
        raises(TypeError, select.epoll, ['foo'])
        raises(TypeError, select.epoll, {})

    def test_add(self):
        import select

        client, server = self.socket_pair()

        ep = select.epoll(2)
        ep.register(server, select.EPOLLIN | select.EPOLLOUT)
        ep.register(client, select.EPOLLIN | select.EPOLLOUT)
        ep.close()

        # adding by object w/ fileno works, too.
        ep = select.epoll(2)
        ep.register(server.fileno(), select.EPOLLIN | select.EPOLLOUT)
        ep.register(client.fileno(), select.EPOLLIN | select.EPOLLOUT)
        ep.close()

        ep = select.epoll(2)
        # TypeError: argument must be an int, or have a fileno() method.
        raises(TypeError, ep.register, object(), select.EPOLLIN | select.EPOLLOUT)
        raises(TypeError, ep.register, None, select.EPOLLIN | select.EPOLLOUT)
        # ValueError: file descriptor cannot be a negative integer (-1)
        raises(ValueError, ep.register, -1, select.EPOLLIN | select.EPOLLOUT)
        # IOError: [Errno 9] Bad file descriptor
        raises(IOError, ep.register, 10000, select.EPOLLIN | select.EPOLLOUT)
        # registering twice also raises an exception
        ep.register(server, select.EPOLLIN | select.EPOLLOUT)
        raises(IOError, ep.register, server, select.EPOLLIN | select.EPOLLOUT)
        ep.close()

    def test_fromfd(self):
        import errno
        import select

        client, server = self.socket_pair()

        ep1 = select.epoll(2)
        ep2 = select.epoll.fromfd(ep1.fileno())

        ep2.register(server.fileno(), select.EPOLLIN | select.EPOLLOUT)
        ep2.register(client.fileno(), select.EPOLLIN | select.EPOLLOUT)

        events1 = ep1.poll(1, 4)
        events2 = ep2.poll(0.9, 4)
        assert len(events1) == 2
        assert len(events2) == 2
        ep1.close()

        exc_info = raises(IOError, ep2.poll, 1, 4)
        assert exc_info.value.args[0] == errno.EBADF

    def test_control_and_wait(self):
        import select
        import time

        client, server = self.socket_pair()

        ep = select.epoll(16)
        ep.register(server.fileno(),
            select.EPOLLIN | select.EPOLLOUT | select.EPOLLET
        )
        ep.register(client.fileno(),
            select.EPOLLIN | select.EPOLLOUT | select.EPOLLET
        )

        now = time.time()
        events = ep.poll(1, 4)
        then = time.time()
        assert then - now < 0.1

        events.sort()
        expected = [
            (client.fileno(), select.EPOLLOUT),
            (server.fileno(), select.EPOLLOUT)
        ]
        expected.sort()

        assert events == expected
        assert then - now < 0.02

        now = time.time()
        events = ep.poll(timeout=2.1, maxevents=4)
        then = time.time()
        assert not events

        client.send("Hello!")
        server.send("world!!!")

        now = time.time()
        events = ep.poll(1, 4)
        then = time.time()
        assert then - now < 0.02

        events.sort()
        expected = [
            (client.fileno(), select.EPOLLIN | select.EPOLLOUT),
            (server.fileno(), select.EPOLLIN | select.EPOLLOUT)
        ]
        expected.sort()

        assert events == expected

        ep.unregister(client.fileno())
        ep.modify(server.fileno(), select.EPOLLOUT)

        now = time.time()
        events = ep.poll(1, 4)
        then = time.time()
        assert then - now < 0.02

        expected = [(server.fileno(), select.EPOLLOUT)]
        assert events == expected

    def test_errors(self):
        import select

        raises(ValueError, select.epoll, -2)
        raises(ValueError, select.epoll().register, -1, select.EPOLLIN)

    def test_unregister_closed(self):
        import select
        import time

        client, server = self.socket_pair()

        fd = server.fileno()
        ep = select.epoll(16)
        ep.register(server)

        now = time.time()
        ep.poll(1, 4)
        then = time.time()
        assert then - now < 0.02

        server.close()
        ep.unregister(fd)
