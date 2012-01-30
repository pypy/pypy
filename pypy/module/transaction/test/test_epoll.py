import py
from pypy.conftest import gettestobjspace


class AppTestEpoll: 
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['transaction', 'select'])

    def test_non_transactional(self):
        import select, posix as os
        fd_read, fd_write = os.pipe()
        epoller = select.epoll()
        epoller.register(fd_read)
        os.write(fd_write, 'x')
        [(fd, events)] = epoller.poll()
        assert fd == fd_read
        assert events & select.EPOLLIN
        got = os.read(fd_read, 1)
        assert got == 'x'

    def test_simple(self):
        import transaction, select, posix as os

        steps = []

        fd_read, fd_write = os.pipe()

        epoller = select.epoll()
        epoller.register(fd_read)

        def write_stuff():
            os.write(fd_write, 'x')
            steps.append('write_stuff')

        class Done(Exception):
            pass

        def callback(fd, events):
            assert fd == fd_read
            assert events & select.EPOLLIN
            got = os.read(fd_read, 1)
            assert got == 'x'
            steps.append('callback')
            raise Done

        transaction.add_epoll(epoller, callback)
        transaction.add(write_stuff)

        assert steps == []
        raises(Done, transaction.run)
        assert steps == ['write_stuff', 'callback']
