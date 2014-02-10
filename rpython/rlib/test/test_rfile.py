
import os
from rpython.rtyper.test.tool import BaseRtypingTest
from rpython.tool.udir import udir
from rpython.rlib import rfile

class TestFile(BaseRtypingTest):
    def setup_class(cls):
        cls.tmpdir = udir.join('test_rfile')
        cls.tmpdir.ensure(dir=True)

    def test_open(self):
        fname = str(self.tmpdir.join('file_1'))

        def f():
            f = open(fname, "w")
            f.write("dupa")
            f.close()

        self.interpret(f, [])
        assert open(fname, "r").read() == "dupa"

    def test_read_write(self):
        fname = str(self.tmpdir.join('file_2'))

        def f():
            f = open(fname, "w")
            f.write("dupa")
            f.close()
            f2 = open(fname)
            dupa = f2.read()
            assert dupa == "dupa"
            f2.close()

        self.interpret(f, [])

    def test_read_sequentially(self):
        fname = self.tmpdir.join('file_3')
        fname.write("dupa")
        fname = str(fname)

        def f():
            f = open(fname)
            a = f.read(1)
            b = f.read(1)
            c = f.read(1)
            d = f.read(1)
            e = f.read()
            f.close()
            assert a == "d"
            assert b == "u"
            assert c == "p"
            assert d == "a"
            assert e == ""

        self.interpret(f, [])

    def test_seek(self):
        fname = str(self.tmpdir.join('file_4'))

        def f():
            f = open(fname, "w+")
            f.write("xxx")
            f.seek(0)
            assert f.read() == "xxx"
            f.close()

        f()
        self.interpret(f, [])

    def test_tempfile(self):
        def f():
            f = os.tmpfile()
            f.write("xxx")
            f.seek(0)
            assert f.read() == "xxx"
            f.close()

        f()
        self.interpret(f, [])

    def test_fileno(self):
        fname = str(self.tmpdir.join('file_5'))

        def f():
            f = open(fname, "w")
            try:
                return f.fileno()
            finally:
                f.close()

        res = self.interpret(f, [])
        assert res > 2

    def test_tell(self):
        fname = str(self.tmpdir.join('file_tell'))

        def f():
            f = open(fname, "w")
            f.write("xyz")
            try:
                return f.tell()
            finally:
                f.close()

        res = self.interpret(f, [])
        assert res == 3

    def test_flush(self):
        fname = str(self.tmpdir.join('file_flush'))

        def f():
            f = open(fname, "w")
            f.write("xyz")
            f.flush()
            f2 = open(fname)
            assert f2.read() == "xyz"
            f2.close()
            f.close()

        self.interpret(f, [])

    def test_truncate(self):
        fname = str(self.tmpdir.join('file_trunc'))

        def f():
            f = open(fname, "w")
            f.write("xyz")
            f.seek(0)
            f.truncate(2)
            f.close()
            f2 = open(fname)
            assert f2.read() == "xy"
            f2.close()

        f()
        self.interpret(f, [])


class TestDirect:
    def setup_class(cls):
        cls.tmpdir = udir.join('test_rfile_direct')
        cls.tmpdir.ensure(dir=True)

    def test_read_a_lot(self):
        fname = str(self.tmpdir.join('file_read_a_lot'))
        with open(fname, 'w') as f:
            f.write('dupa' * 999)
        f = rfile.create_file(fname, 'r')
        s = f.read()
        assert s == 'dupa' * 999
        f.close()

    def test_readline(self):
        fname = str(self.tmpdir.join('file_readline'))
        j = 0
        expected = []
        with open(fname, 'w') as f:
            for i in range(250):
                s = ''.join([chr(32+(k&63)) for k in range(j, j + i)])
                j += 1
                print >> f, s
        expected = open(fname).readlines()
        expected += ['', '']
        assert len(expected) == 252

        f = rfile.create_file(fname, 'r')
        for j in range(252):
            got = f.readline()
            assert got == expected[j]
        f.close()

    def test_readline_without_eol_at_the_end(self):
        fname = str(self.tmpdir.join('file_readline_without_eol_at_the_end'))
        for n in [1, 10, 97, 98, 99, 100, 101, 102, 103, 150,
                  196, 197, 198, 199, 200, 201, 202, 203, 204, 250]:
            s = ''.join([chr(32+(k&63)) for k in range(n)])
            with open(fname, 'wb') as f:
                f.write(s)

            f = rfile.create_file(fname, 'r')
            got = f.readline()
            assert got == s
            got = f.readline()
            assert got == ''
            f.close()
