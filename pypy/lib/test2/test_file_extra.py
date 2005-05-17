import os, random
from pypy.lib import _file 
from pypy.tool.udir import udir 
import py 

class TestFile: 
    def setup_method(self, method):
        self.fd = _file.file(__file__, 'r')

    def teardown_method(self, method):
        self.fd.close()
        
    def test_case_1(self):
        assert self.fd.tell() == 0

    def test_case_readonly(self):
        fn = str(udir.join('temptestfile'))
        f=_file.file(fn, 'w')
        assert f.name == fn
        assert f.mode == 'w'
        assert f.closed == False
        assert f.encoding == None # Fix when we find out what this is
        py.test.raises((TypeError, AttributeError), setattr, f, 'name', 42)

    def test_plain_read(self):
        data1 = self.fd.read()
        data2 = open(__file__, 'r').read()
        assert data1 == data2

    def test_readline(self):
        cpyfile = open(__file__, 'r')
        assert self.fd.readline() == cpyfile.readline()
        for i in range(-1, 10):
            assert self.fd.readline(i) == cpyfile.readline(i)

    def test_readlines(self):
        fn = str(udir.join('temptestfile'))
        lines = ['line%d\n' % i for i in range(1000)]
        f=_file.file(fn, 'w')
        f.writelines(lines)
        f.close()
        assert open(fn, 'r').readlines() == lines
        assert _file.file(fn, 'r').readlines() == lines
        somelines = _file.file(fn, 'r').readlines(2000)
        assert len(somelines) > 200
        assert somelines == lines[:len(somelines)]

    def stresstest(self, flags, checkflags, eolstyles):
        fn = str(udir.join('temptestfile'))
        f = _file.file(fn, flags)
        expected = ''
        pos = 0
        for i in range(5000):
            x = random.random()
            if x < 0.4:
                l = int(x*100)
                buf = f.read(l)
                assert buf == expected[pos:pos+l]
                pos += len(buf)
            elif x < 0.75:
                writeeol, expecteol = random.choice(eolstyles)
                x = str(x)
                buf1 = x+writeeol
                buf2 = x+expecteol
                f.write(buf1)
                expected = expected[:pos] + buf2 + expected[pos+len(buf2):]
                pos += len(buf2)
            elif x < 0.80:
                pos = random.randint(0, len(expected))
                f.seek(pos)
            elif x < 0.85:
                pos = random.randint(0, len(expected))
                f.seek(pos - len(expected), 2)
            elif x < 0.90:
                currentpos = pos
                pos = random.randint(0, len(expected))
                f.seek(pos - currentpos, 1)
            elif x < 0.95:
                assert f.tell() == pos
            else:
                f.flush()
                g = open(fn, checkflags)
                buf = g.read()
                g.close()
                assert buf == expected
        f.close()
        g = open(fn, checkflags)
        buf = g.read()
        g.close()
        assert buf == expected

    def test_rw_bin(self):
        self.stresstest('w+b', 'rb', [('', ''),     ('\n', '\n'),
                                      ('\r', '\r'), ('\r\n', '\r\n')])

    def test_rw(self):
        # XXX tests in progress
        fn = str(udir.join('temptestfile'))
        f = _file.file(fn, 'w+')
        f.write('hello\nworld\n')
        f.seek(0)
        assert f.read() == 'hello\nworld\n'
        f.close()

    def test_rw_universal(self):
        # XXX tests in progress
        fn = str(udir.join('temptestfile'))
        f = _file.file(fn, 'w+U')
        f.write('hello\r\nworld\r\n')
        f.seek(0)
        assert f.read() == 'hello\nworld\n'
        f.close()
