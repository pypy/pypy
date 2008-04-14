
from pypy.conftest import gettestobjspace

import os, sys, py


class AppTestcStringIO:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('cStringIO',))
        cls.space = space
        cls.w_write_many_expected_result = space.wrap(''.join(
            [chr(i) for j in range(10) for i in range(253)]))
        cls.w_StringIO = space.appexec([], """():
            import cStringIO
            return cStringIO.StringIO
        """)

    def test_simple(self):
        f = self.StringIO()
        f.write('hello')
        f.write(' world')
        assert f.getvalue() == 'hello world'

    def test_write_many(self):
        f = self.StringIO()
        for j in range(10):
            for i in range(253):
                f.write(chr(i))
        expected = ''.join([chr(i) for j in range(10) for i in range(253)])
        assert f.getvalue() == expected

    def test_seek(self):
        f = self.StringIO()
        f.write('0123')
        f.write('456')
        f.write('789')
        f.seek(4)
        f.write('AB')
        assert f.getvalue() == '0123AB6789'
        f.seek(-2, 2)
        f.write('CDE')
        assert f.getvalue() == '0123AB67CDE'
        f.seek(2, 0)
        f.seek(5, 1)
        f.write('F')
        assert f.getvalue() == '0123AB6FCDE'

    def test_write_beyond_end(self):
        f = self.StringIO()
        f.seek(20, 1)
        assert f.tell() == 20
        f.write('X')
        assert f.getvalue() == '\x00' * 20 + 'X'

    def test_tell(self):
        f = self.StringIO()
        f.write('0123')
        f.write('456')
        assert f.tell() == 7
        f.seek(2)
        for i in range(3, 20):
            f.write('X')
            assert f.tell() == i
        assert f.getvalue() == '01XXXXXXXXXXXXXXXXX'

    def test_read(self):
        f = self.StringIO()
        assert f.read() == ''
        f.write('0123')
        f.write('456')
        assert f.read() == ''
        assert f.read(5) == ''
        assert f.tell() == 7
        f.seek(1)
        assert f.read() == '123456'
        assert f.tell() == 7
        f.seek(1)
        assert f.read(12) == '123456'
        assert f.tell() == 7
        f.seek(1)
        assert f.read(2) == '12'
        assert f.read(1) == '3'
        assert f.tell() == 4
        f.seek(0)
        assert f.read() == '0123456'
        assert f.tell() == 7
        f.seek(0)
        assert f.read(7) == '0123456'
        assert f.tell() == 7
        f.seek(15)
        assert f.read(2) == ''
        assert f.tell() == 15

    def test_reset(self):
        f = self.StringIO()
        f.write('foobar')
        f.reset()
        res = f.read()
        assert res == 'foobar'

    def test_close(self):
        f = self.StringIO()
        assert not f.closed
        f.close()
        raises(ValueError, f.write, 'hello')
        raises(ValueError, f.getvalue)
        raises(ValueError, f.read, 0)
        raises(ValueError, f.seek, 0)
        assert f.closed
        f.close()
        assert f.closed

    def test_readline(self):
        f = self.StringIO()
        f.write('foo\nbar\nbaz')
        f.seek(0)
        assert f.readline() == 'foo\n'
        assert f.readline(2) == 'ba'
        assert f.readline() == 'r\n'
        assert f.readline() == 'baz'
        assert f.readline() == ''
        f.seek(0)
        assert iter(f) is f
        assert list(f) == ['foo\n', 'bar\n', 'baz']
        f.write('\n')
        f.seek(0)
        assert iter(f) is f
        assert list(f) == ['foo\n', 'bar\n', 'baz\n']
        f.seek(0)
        assert f.readlines() == ['foo\n', 'bar\n', 'baz\n']
        f.seek(0)
        assert f.readlines(2) == ['foo\n']

    def test_misc(self):
        f = self.StringIO()
        f.flush()
        assert f.isatty() is False

    def test_truncate(self):
        f = self.StringIO()
        f.truncate(20)
        assert f.getvalue() == ''
        assert f.tell() == 0
        f.write('\x00' * 20)
        f.write('hello')
        f.write(' world')
        f.truncate(30)
        assert f.getvalue() == '\x00' * 20 + 'hello worl'
        f.truncate(25)
        assert f.getvalue() == '\x00' * 20 + 'hello'
        f.write('baz')
        f.write('egg')
        f.truncate(3)
        assert f.tell() == 3
        assert f.getvalue() == '\x00' * 3
        raises(IOError, f.truncate, -1)

    def test_writelines(self):
        f = self.StringIO()
        f.writelines(['foo', 'bar', 'baz'])
        assert f.getvalue() == 'foobarbaz'

    def test_stringi(self):
        f = self.StringIO('hello world\nspam\n')
        assert not hasattr(f, 'write')      # it's a StringI
        f.seek(3)
        assert f.tell() == 3
        f.seek(50, 1)
        assert f.tell() == 53
        f.seek(-3, 2)
        assert f.tell() == 14
        assert f.read() == 'am\n'
        f.seek(0)
        assert f.readline() == 'hello world\n'
        assert f.readline(4) == 'spam'
        assert f.readline(400) == '\n'
        f.reset()
        assert f.readlines() == ['hello world\n', 'spam\n']
        f.seek(0, 0)
        assert f.readlines(5) == ['hello world\n']
        f.seek(0)
        assert list(f) == ['hello world\n', 'spam\n']

        f.flush()
        assert f.getvalue() == 'hello world\nspam\n'
        assert f.isatty() is False

        assert not f.closed
        f.close()
        assert f.closed
        raises(ValueError, f.flush)
        raises(ValueError, f.getvalue)
        raises(ValueError, f.isatty)
        raises(ValueError, f.read)
        raises(ValueError, f.readline)
        raises(ValueError, f.readlines)
        raises(ValueError, f.reset)
        raises(ValueError, f.tell)
        raises(ValueError, f.seek, 5)
        assert f.closed
        f.close()
        assert f.closed

    def test_types(self):
        import cStringIO
        assert type(cStringIO.StringIO()) is cStringIO.OutputType
        assert type(cStringIO.StringIO('')) is cStringIO.InputType
