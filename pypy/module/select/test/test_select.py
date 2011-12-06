import py, sys
from pypy.conftest import gettestobjspace

class _AppTestSelect:
    def test_sleep(self):
        """
        The timeout parameter to select.select specifies the approximate
        maximum amount of time for that function to block before it returns
        to report that no results are available.
        """
        import time, select
        readend, writeend = self.getpair()
        try:
            start = time.time()
            iwtd, owtd, ewtd = select.select([readend], [], [], 0.3)
            end = time.time()
            assert iwtd == owtd == ewtd == []
            assert end - start > 0.25
        finally:
            readend.close()
            writeend.close()

    def test_list_tuple(self):
        import time, select
        readend, writeend = self.getpair()
        try:
            iwtd, owtd, ewtd = select.select([readend], (), (), .3)
        finally:
            readend.close()
            writeend.close()

    def test_readable(self):
        """
        select.select returns elements from the "read list" (the first
        parameter) which may have data available to be read.
        """
        import select
        readend, writeend = self.getpair()
        try:
            iwtd, owtd, ewtd = select.select([readend], [], [], 0)
            assert iwtd == owtd == ewtd == []
            writeend.send('X')
            iwtd, owtd, ewtd = select.select([readend], [], [])
            assert iwtd == [readend]
            assert owtd == ewtd == []
        finally:
            writeend.close()
            readend.close()

    def test_writable(self):
        """
        select.select returns elements from the "write list" (the second
        parameter) on which a write/send may be possible.
        """
        import select
        readend, writeend = self.getpair()
        try:
            iwtd, owtd, ewtd = select.select([], [writeend], [], 0)
            assert iwtd == ewtd == []
            assert owtd == [writeend]
        finally:
            writeend.close()
            readend.close()

    def test_write_read(self):
        """
        select.select returns elements from the "write list" (the second
        parameter) on which a write/send may be possible.  select.select
        returns elements from the "read list" (the first parameter) which
        may have data available to be read. (the second part of this test
        overlaps significantly with test_readable. -exarkun)
        """
        import select
        readend, writeend = self.getpair()
        try:
            total_out = 0
            while True:
                iwtd, owtd, ewtd = select.select([], [writeend], [], 0)
                assert iwtd == ewtd == []
                if owtd == []:
                    break
                assert owtd == [writeend]
                total_out += writeend.send('x' * 512)
            total_in = 0
            while True:
                iwtd, owtd, ewtd = select.select([readend], [], [], 0)
                assert owtd == ewtd == []
                if iwtd == []:
                    break
                assert iwtd == [readend]
                data = readend.recv(4096)
                assert len(data) > 0
                assert data == 'x' * len(data)
                total_in += len(data)
            assert total_in == total_out
        finally:
            writeend.close()
            readend.close()

    def test_write_close(self):
        """
        select.select returns elements from the "read list" (the first
        parameter) which have no data to be read but which have been closed.
        """
        import select, sys
        readend, writeend = self.getpair()
        try:
            try:
                total_out = writeend.send('x' * 512)
            finally:
                # win32 sends the 'closed' event immediately, even when
                # more data is available
                if sys.platform != 'win32':
                    writeend.close()
                    import gc; gc.collect()
            assert 1 <= total_out <= 512
            total_in = 0
            while True:
                iwtd, owtd, ewtd = select.select([readend], [], [])
                assert iwtd == [readend]
                assert owtd == ewtd == []
                data = readend.recv(4096)
                if len(data) == 0:
                    break
                assert data == 'x' * len(data)
                total_in += len(data)
                # win32: check that closing the socket exits the loop
                if sys.platform == 'win32' and total_in == total_out:
                    writeend.close()
            assert total_in == total_out
        finally:
            readend.close()

    def test_read_closed(self):
        """
        select.select returns elements from the "read list" (the first
        parameter) which are at eof (even if they are the write end of a
        pipe).
        """
        import select
        readend, writeend = self.getpair()
        try:
            readend.close()
            import gc; gc.collect()
            iwtd, owtd, ewtd = select.select([writeend], [], [], 0)
            assert iwtd == [writeend]
            assert owtd == ewtd == []
        finally:
            writeend.close()

    def test_read_many(self):
        """
        select.select returns only the elements from the "read list" (the
        first parameter) which may have data available to be read.
        (test_readable has a lot of overlap with this test. -exarkun)
        """
        import select
        readends = []
        writeends = []
        try:
            for i in range(10):
                fd1, fd2 = self.getpair()
                readends.append(fd1)
                writeends.append(fd2)
            iwtd, owtd, ewtd = select.select(readends, [], [], 0)
            assert iwtd == owtd == ewtd == []

            for i in range(50):
                n = (i*3) % 10
                writeends[n].send('X')
                iwtd, owtd, ewtd = select.select(readends, [], [])
                assert iwtd == [readends[n]]
                assert owtd == ewtd == []
                data = readends[n].recv(1)
                assert data == 'X'

        finally:
            for fd in readends + writeends:
                fd.close()

    def test_read_end_closed(self):
        """
        select.select returns elements from the "write list" (the second
        parameter) when they are not writable but when the corresponding
        read end has been closed. (this test currently doesn't make the
        write end non-writable before testing its selectability. -exarkun)
        """
        import select
        readend, writeend = self.getpair()
        readend.close()
        try:
            iwtd, owtd, ewtd = select.select([], [writeend], [])
            assert owtd == [writeend]
            assert iwtd == ewtd == []
        finally:
            writeend.close()

    def test_select_bug(self):
        import select, os
        if not hasattr(os, 'fork'):
            skip("no fork() on this platform")
        read, write = os.pipe()
        pid = os.fork()
        if pid == 0:
            os._exit(0)
        else:
            os.close(read)
        os.waitpid(pid, 0)
        res = select.select([write], [write], [write])
        assert len(res[0]) == 1
        assert len(res[1]) == 1
        assert len(res[2]) == 0
        assert res[0][0] == res[1][0]

    def test_poll(self):
        import select
        readend, writeend = self.getpair()
        try:
            class A(object):
                def __int__(self):
                    return readend.fileno()
            select.poll().poll(A()) # assert did not crash
        finally:
            readend.close()
            writeend.close()

class AppTestSelectWithPipes(_AppTestSelect):
    "Use a pipe to get pairs of file descriptors"
    def setup_class(cls):
        if sys.platform == 'win32':
            py.test.skip("select() doesn't work with pipes on win32")
        space = gettestobjspace(usemodules=('select',))
        cls.space = space

    def w_getpair(self):
        # Wraps a file descriptor in an socket-like object
        import os
        class FileAsSocket:
            def __init__(self, fd):
                self.fd = fd
            def fileno(self):
                return self.fd
            def send(self, data):
                return os.write(self.fd, data)
            def recv(self, length):
                return os.read(self.fd, length)
            def close(self):
                return os.close(self.fd)
        s1, s2 = os.pipe()
        return FileAsSocket(s1), FileAsSocket(s2)

class AppTestSelectWithSockets(_AppTestSelect):
    """Same tests with connected sockets.
    socket.socketpair() does not exists on win32,
    so we start our own server."""
    def setup_class(cls):
        space = gettestobjspace(usemodules=('select','_socket'))
        cls.space = space

        cls.w_getpair = space.wrap(cls.getsocketpair)

        import socket
        cls.sock = socket.socket()

        try_ports = [1023] + range(20000, 30000, 437)
        for port in try_ports:
            print 'binding to port %d:' % (port,),
            cls.sockaddress = ('127.0.0.1', port)
            try:
                cls.sock.bind(cls.sockaddress)
                print 'works'
                break
            except socket.error, e:   # should get a "Permission denied"
                print e
            else:
                raise e

    @classmethod
    def getsocketpair(cls):
        """Helper method which returns a pair of connected sockets.
        Note that they become faked objects at AppLevel"""
        import thread, socket

        cls.sock.listen(1)
        s2 = socket.socket()
        thread.start_new_thread(s2.connect, (cls.sockaddress,))
        s1, addr2 = cls.sock.accept()

        return s1, s2
