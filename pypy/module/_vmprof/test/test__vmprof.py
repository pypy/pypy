from rpython.tool.udir import udir
from pypy.tool.pytest.objspace import gettestobjspace

class AppTestVMProf(object):
    spaceconfig = {'usemodules': ['_vmprof', 'struct']}

    def setup_class(cls):
        cls.w_tmpfilename = cls.space.wrap(str(udir.join('test__vmprof.1')))
        cls.w_tmpfilename2 = cls.space.wrap(str(udir.join('test__vmprof.2')))

    def test_import_vmprof(self):
        tmpfile = open(self.tmpfilename, 'wb')
        tmpfileno = tmpfile.fileno()
        tmpfile2 = open(self.tmpfilename2, 'wb')
        tmpfileno2 = tmpfile2.fileno()

        import struct, sys, gc

        WORD = struct.calcsize('l')

        def count(s):
            i = 0
            count = 0
            i += 5 * WORD # header
            assert s[i    ] == '\x05'    # MARKER_HEADER
            assert s[i + 1] == '\x00'    # 0
            assert s[i + 2] == '\x06'    # VERSION_TIMESTAMP
            assert s[i + 3] == '\x08'    # PROFILE_RPYTHON
            assert s[i + 4] == chr(4)    # len('pypy')
            assert s[i + 5: i + 9] == 'pypy'
            i += 9
            while i < len(s):
                if s[i] == '\x03':
                    break
                elif s[i] == '\x01':
                    i += 1
                    _, size = struct.unpack("ll", s[i:i + 2 * WORD])
                    i += 2 * WORD + size * struct.calcsize("P")
                    i += WORD    # thread id
                elif s[i] == '\x02':
                    i += 1
                    _, size = struct.unpack("ll", s[i:i + 2 * WORD])
                    count += 1
                    i += 2 * WORD + size
                elif s[i] == '\x06':
                    i += 8+8+8
                else:
                    raise AssertionError(ord(s[i]))
            return count

        import _vmprof
        gc.collect()  # try to make the weakref list deterministic
        gc.collect()  # by freeing all dead code objects
        _vmprof.enable(tmpfileno, 0.01, 0, 0, 0)
        _vmprof.disable()
        s = open(self.tmpfilename, 'rb').read()
        no_of_codes = count(s)
        assert no_of_codes > 10
        d = {}

        exec """def foo():
            pass
        """ in d

        gc.collect()
        gc.collect()
        _vmprof.enable(tmpfileno2, 0.01, 0, 0, 0)

        exec """def foo2():
            pass
        """ in d

        _vmprof.disable()
        s = open(self.tmpfilename2, 'rb').read()
        no_of_codes2 = count(s)
        assert "py:foo:" in s
        assert "py:foo2:" in s
        assert no_of_codes2 >= no_of_codes + 2 # some extra codes from tests

    def test_enable_ovf(self):
        import _vmprof
        raises(_vmprof.VMProfError, _vmprof.enable, 2, 0, 0, 0, 0)
        raises(_vmprof.VMProfError, _vmprof.enable, 2, -2.5, 0, 0, 0)
        raises(_vmprof.VMProfError, _vmprof.enable, 2, 1e300, 0, 0, 0)
        raises(_vmprof.VMProfError, _vmprof.enable, 2, 1e300 * 1e300, 0, 0, 0)
        NaN = (1e300*1e300) / (1e300*1e300)
        raises(_vmprof.VMProfError, _vmprof.enable, 2, NaN, 0, 0, 0)
