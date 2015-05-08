
import tempfile
from pypy.tool.pytest.objspace import gettestobjspace

class AppTestVMProf(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_vmprof', 'struct'])
        cls.tmpfile = tempfile.NamedTemporaryFile()
        cls.w_tmpfileno = cls.space.wrap(cls.tmpfile.fileno())
        cls.w_tmpfilename = cls.space.wrap(cls.tmpfile.name)
        cls.tmpfile2 = tempfile.NamedTemporaryFile()
        cls.w_tmpfileno2 = cls.space.wrap(cls.tmpfile2.fileno())
        cls.w_tmpfilename2 = cls.space.wrap(cls.tmpfile2.name)

    def test_import_vmprof(self):
        import struct, sys

        WORD = struct.calcsize('l')
        
        def count(s):
            i = 0
            count = 0
            i += 5 * WORD # header
            assert s[i] == '\x04'
            i += 1 # marker
            assert s[i] == '\x04'
            i += 1 # length
            i += len('pypy')
            while i < len(s):
                if s[i] == '\x03':
                    break
                if s[i] == '\x01':
                    xxx
                assert s[i] == '\x02'
                i += 1
                _, size = struct.unpack("ll", s[i:i + 2 * WORD])
                count += 1
                i += 2 * WORD + size
            return count
        
        import _vmprof
        _vmprof.enable(self.tmpfileno)
        _vmprof.disable()
        s = open(self.tmpfilename).read()
        no_of_codes = count(s)
        assert no_of_codes > 10
        d = {}

        exec """def foo():
            pass
        """ in d

        _vmprof.enable(self.tmpfileno2)

        exec """def foo2():
            pass
        """ in d

        _vmprof.disable()
        s = open(self.tmpfilename2).read()
        no_of_codes2 = count(s)
        assert "py:foo:" in s
        assert "py:foo2:" in s
        assert no_of_codes2 >= no_of_codes + 2 # some extra codes from tests

    def test_enable_ovf(self):
        import _vmprof
        raises(ValueError, _vmprof.enable, 999, 0)
        raises(ValueError, _vmprof.enable, 999, -2.5)
        raises(ValueError, _vmprof.enable, 999, 1e300)
        raises(ValueError, _vmprof.enable, 999, 1e300 * 1e300)
        raises(ValueError, _vmprof.enable, 999, (1e300*1e300) / (1e300*1e300))
