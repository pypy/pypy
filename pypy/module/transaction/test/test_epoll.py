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

    def test_remove_closed_epoll(self):
        import transaction, select, posix as os

        fd_read, fd_write = os.pipe()

        epoller = select.epoll()
        epoller.register(fd_read)

        # we run it 10 times in order to get both possible orders in
        # the emulator
        for i in range(10):
            transaction.add_epoll(epoller, lambda *args: not_actually_callable)
            transaction.add(transaction.remove_epoll, epoller)
            transaction.run()
            # assert didn't deadlock
            transaction.add(transaction.remove_epoll, epoller)
            transaction.add_epoll(epoller, lambda *args: not_actually_callable)
            transaction.run()
            # assert didn't deadlock

    def test_errors(self):
        import transaction, select
        epoller = select.epoll()
        callback = lambda *args: not_actually_callable
        transaction.add_epoll(epoller, callback)
        raises(transaction.TransactionError,
               transaction.add_epoll, epoller, callback)
        transaction.remove_epoll(epoller)
        raises(transaction.TransactionError,
               transaction.remove_epoll, epoller)


class AppTestEpollEmulator(AppTestEpoll):
    def setup_class(cls):
        # test for lib_pypy/transaction.py
        cls.space = gettestobjspace(usemodules=['select'])
