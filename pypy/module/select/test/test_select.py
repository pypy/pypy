import py, sys
from pypy.conftest import gettestobjspace

class AppTestSelect:
    def setup_class(cls):
        if sys.platform == 'win':
            py.test.skip("select() doesn't work with pipes, "
                         "we would need tests using sockets")
        space = gettestobjspace(usemodules=('select',))
        cls.space = space

    def test_sleep(self):
        import time, select
        start = time.time()
        iwtd, owtd, ewtd = select.select([], [], [], 0.3)
        end = time.time()
        assert iwtd == owtd == ewtd == []
        assert end - start > 0.25

    def test_readable(self):
        import os, select
        readend, writeend = os.pipe()
        try:
            iwtd, owtd, ewtd = select.select([readend], [], [], 0)
            assert iwtd == owtd == ewtd == []
            os.write(writeend, 'X')
            iwtd, owtd, ewtd = select.select([readend], [], [])
            assert iwtd == [readend]
            assert owtd == ewtd == []
        finally:
            os.close(writeend)
            os.close(readend)

    def test_write_read(self):
        import os, select
        readend, writeend = os.pipe()
        try:
            total_out = 0
            while True:
                iwtd, owtd, ewtd = select.select([], [writeend], [], 0)
                assert iwtd == ewtd == []
                if owtd == []:
                    break
                assert owtd == [writeend]
                total_out += os.write(writeend, 'x' * 512)
            total_in = 0
            while True:
                iwtd, owtd, ewtd = select.select([readend], [], [], 0)
                assert owtd == ewtd == []
                if iwtd == []:
                    break
                assert iwtd == [readend]
                data = os.read(readend, 4096)
                assert len(data) > 0
                assert data == 'x' * len(data)
                total_in += len(data)
            assert total_in == total_out
        finally:
            os.close(writeend)
            os.close(readend)

    def test_close(self):
        import os, select
        readend, writeend = os.pipe()
        try:
            try:
                total_out = os.write(writeend, 'x' * 512)
            finally:
                os.close(writeend)
            assert 1 <= total_out <= 512
            total_in = 0
            while True:
                iwtd, owtd, ewtd = select.select([readend], [], [])
                assert iwtd == [readend]
                assert owtd == ewtd == []
                data = os.read(readend, 4096)
                if len(data) == 0:
                    break
                assert data == 'x' * len(data)
                total_in += len(data)
            assert total_in == total_out
        finally:
            os.close(readend)

    def test_read_many(self):
        import os, select
        readends = []
        writeends = []
        try:
            for i in range(10):
                fd1, fd2 = os.pipe()
                readends.append(fd1)
                writeends.append(fd2)
            iwtd, owtd, ewtd = select.select(readends, [], [], 0)
            assert iwtd == owtd == ewtd == []

            for i in range(50):
                n = (i*3) % 10
                os.write(writeends[n], 'X')
                iwtd, owtd, ewtd = select.select(readends, [], [])
                assert iwtd == [readends[n]]
                assert owtd == ewtd == []
                data = os.read(readends[n], 1)
                assert data == 'X'

        finally:
            for fd in readends + writeends:
                os.close(fd)

    def test_read_end_closed(self):
        import os, select
        readend, writeend = os.pipe()
        os.close(readend)
        try:
            iwtd, owtd, ewtd = select.select([], [writeend], [])
            assert owtd == [writeend]
            assert iwtd == ewtd == []
        finally:
            os.close(writeend)
