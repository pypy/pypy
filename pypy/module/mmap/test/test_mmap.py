from pypy.conftest import gettestobjspace
from pypy.tool.udir import udir
import os

class AppTestMMap:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('mmap',))
        cls.space = space
        cls.w_tmpname = space.wrap(str(udir.join('mmap-')))
    
    def test_page_size(self):
        import mmap
        assert mmap.PAGESIZE > 0
        assert isinstance(mmap.PAGESIZE, int)
        
    def test_attributes(self):
        import mmap
        import os
        assert isinstance(mmap.ACCESS_READ, int)
        assert isinstance(mmap.ACCESS_WRITE, int)
        assert isinstance(mmap.ACCESS_COPY, int)
        if os.name == "posix":
            assert isinstance(mmap.MAP_ANON, int)
            assert isinstance(mmap.MAP_ANONYMOUS, int)
            assert isinstance(mmap.MAP_PRIVATE, int)
            assert isinstance(mmap.MAP_SHARED, int)
            assert isinstance(mmap.PROT_EXEC, int)
            assert isinstance(mmap.PROT_READ, int)
            assert isinstance(mmap.PROT_WRITE, int)
        
        assert mmap.error is EnvironmentError
            
    def test_args(self):
        from mmap import mmap
        import os
        import sys
        
        raises(TypeError, mmap, "foo")
        raises(TypeError, mmap, 0, "foo")
             
        if os.name == "posix":
            raises(TypeError, mmap, 0, 1, 2, 3, 4, 5)
            raises(TypeError, mmap, 0, 1, 2, 3, "foo", 5)
            raises(TypeError, mmap, 0, 1, foo="foo")
            raises(TypeError, mmap, 0, -1)
            raises(OverflowError, mmap, 0, sys.maxint ** 3)
            raises(ValueError, mmap, 0, 1, flags=2, access=3)
            raises(ValueError, mmap, 0, 1, access=123)
        elif os.name == "nt":
            raises(TypeError, mmap, 0, 1, 2, 3, 4)
            raises(TypeError, mmap, 0, 1, tagname=123)
            raises(TypeError, mmap, 0, 1, access="foo")
            raises(ValueError, mmap, 0, 1, access=-1)

    def test_file_size(self):
        import os
        if os.name == "nt":
            skip("Only Unix checks file size")

        from mmap import mmap
        f = open(self.tmpname + "a", "w+")
        
        f.write("c")
        f.flush()
        raises(ValueError, mmap, f.fileno(), 123)
        f.close()

    def test_create(self):
        from mmap import mmap
        f = open(self.tmpname + "b", "w+")
        
        f.write("c")
        f.flush()
        m = mmap(f.fileno(), 1)
        assert m.read(99) == "c"
        
        f.close()

    def test_close(self):
        from mmap import mmap
        f = open(self.tmpname + "c", "w+")
        
        f.write("c")
        f.flush()
        m = mmap(f.fileno(), 1)
        m.close()
        raises(ValueError, m.read, 1)

    def test_read_byte(self):
        from mmap import mmap
        f = open(self.tmpname + "d", "w+")

        f.write("c")
        f.flush()
        m = mmap(f.fileno(), 1)
        assert m.read_byte() == "c"
        raises(ValueError, m.read_byte)
        m.close()
        f.close()

    def test_readline(self):
        from mmap import mmap
        import os
        f = open(self.tmpname + "e", "w+")

        f.write("foo\n")
        f.flush()
        m = mmap(f.fileno(), 4)
        if os.name == "nt":
            # windows replaces \n with \r. it's time to change to \n only MS!
            assert m.readline() == "foo\r"
        elif os.name == "posix":
            assert m.readline() == "foo\n"
        assert m.readline() == ""
        m.close()
        f.close()

    def test_read(self):
        from mmap import mmap
        f = open(self.tmpname + "f", "w+")
        
        f.write("foobar")
        f.flush()
        m = mmap(f.fileno(), 6)
        raises(TypeError, m.read, "foo")
        assert m.read(1) == "f"
        assert m.read(6) == "oobar"
        assert m.read(1) == ""
        m.close()
        f.close()

    def test_find(self):
        from mmap import mmap
        f = open(self.tmpname + "g", "w+")

        f.write("foobar\0")
        f.flush()
        m = mmap(f.fileno(), 7)
        raises(TypeError, m.find, 123)
        raises(TypeError, m.find, "foo", "baz")
        assert m.find("b") == 3
        assert m.find("z") == -1
        assert m.find("o", 5) == -1
        assert m.find("ob") == 2
        assert m.find("\0") == 6
        m.close()
        f.close()

    def test_is_modifiable(self):
        import mmap
        f = open(self.tmpname + "h", "w+")
        
        f.write("foobar")
        f.flush()
        m = mmap.mmap(f.fileno(), 6, access=mmap.ACCESS_READ)
        raises(TypeError, m.write, 'x')
        raises(TypeError, m.resize, 7)
        m.close()
        f.close()

    def test_seek(self):
        from mmap import mmap
        f = open(self.tmpname + "i", "w+")
        
        f.write("foobar")
        f.flush()
        m = mmap(f.fileno(), 6)
        raises(TypeError, m.seek, "foo")
        raises(TypeError, m.seek, 0, "foo")
        raises(ValueError, m.seek, -1, 0)
        raises(ValueError, m.seek, -1, 1)
        raises(ValueError, m.seek, -7, 2)
        raises(ValueError, m.seek, 1, 3)
        raises(ValueError, m.seek, 10)
        m.seek(0)
        assert m.tell() == 0
        m.read(1)
        m.seek(1, 1)
        assert m.tell() == 2
        m.seek(0)
        m.seek(-1, 2)
        assert m.tell() == 5
        m.close()
        f.close()

    def test_write(self):
        import mmap
        f = open(self.tmpname + "j", "w+")

        f.write("foobar")
        f.flush()
        m = mmap.mmap(f.fileno(), 6, access=mmap.ACCESS_READ)
        raises(TypeError, m.write, "foo")
        m = mmap.mmap(f.fileno(), 6, access=mmap.ACCESS_WRITE)
        raises(TypeError, m.write, 123)
        raises(ValueError, m.write, "c"*10)
        m.write("ciao\n")
        m.seek(0)
        assert m.read(6) == "ciao\nr"
        m.close()

    def test_write_byte(self):
        import mmap
        f = open(self.tmpname + "k", "w+")
        
        f.write("foobar")
        f.flush()
        m = mmap.mmap(f.fileno(), 6, access=mmap.ACCESS_READ)
        raises(TypeError, m.write_byte, "f")
        m = mmap.mmap(f.fileno(), 6, access=mmap.ACCESS_WRITE)
        raises(TypeError, m.write_byte, 123)
        raises(TypeError, m.write_byte, "ab")
        m.write_byte("x")
        m.seek(0)
        assert m.read(6) == "xoobar"
        m.close()

    def test_size(self):
        from mmap import mmap
        f = open(self.tmpname + "l", "w+")
        
        f.write("foobar")
        f.flush()
        m = mmap(f.fileno(), 5)
        assert m.size() == 6 # size of the underline file, not the mmap
        m.close()
        f.close()

    def test_tell(self):
        from mmap import mmap
        f = open(self.tmpname + "m", "w+")
        
        f.write("c")
        f.flush()
        m = mmap(f.fileno(), 1)
        assert m.tell() >= 0
        m.close()
        f.close()

    def test_flush(self):
        from mmap import mmap
        f = open(self.tmpname + "n", "w+")
        
        f.write("foobar")
        f.flush()
        m = mmap(f.fileno(), 6)
        raises(TypeError, m.flush, 1, 2, 3)
        raises(TypeError, m.flush, 1, "a")
        raises(ValueError, m.flush, 0, 99)
        m.flush()    # return value is a bit meaningless, platform-dependent
        m.close()
        f.close()

    def test_move(self):
        import mmap
        f = open(self.tmpname + "o", "w+")
        
        f.write("foobar")
        f.flush()
        m = mmap.mmap(f.fileno(), 6, access=mmap.ACCESS_READ)
        raises(TypeError, m.move, 1)
        raises(TypeError, m.move, 1, "foo", 2)
        m = mmap.mmap(f.fileno(), 6, access=mmap.ACCESS_WRITE)
        raises(ValueError, m.move, 7, 1, 2)
        raises(ValueError, m.move, 1, 7, 2)
        m.move(1, 3, 3)
        assert m.read(6) == "fbarar"
        m.seek(0)
        m.move(1, 3, 2)
        a = m.read(6)
        assert a == "frarar"
        m.close()
        f.close()
    
    def test_resize(self):
        import sys
        if ("darwin" in sys.platform) or ("freebsd" in sys.platform):
            skip("resize does not work under OSX or FreeBSD")
        
        import mmap
        import os
        
        f = open(self.tmpname + "p", "w+")
        f.write("foobar")
        f.flush()
        m = mmap.mmap(f.fileno(), 6, access=mmap.ACCESS_READ)
        raises(TypeError, m.resize, 1)
        m = mmap.mmap(f.fileno(), 6, access=mmap.ACCESS_COPY)
        raises(TypeError, m.resize, 1)
        m = mmap.mmap(f.fileno(), 6, access=mmap.ACCESS_WRITE)
        f_size = os.fstat(f.fileno()).st_size
        assert m.size() == f_size == 6
        m.resize(10)
        f_size = os.fstat(f.fileno()).st_size
        assert m.size() == f_size == 10
        m.close()
        f.close()

    def test_len(self):
        from mmap import mmap
        
        f = open(self.tmpname + "q", "w+")
        f.write("foobar")
        f.flush()

        m = mmap(f.fileno(), 6)
        assert len(m) == 6
        m.close()
        f.close()
     
    def test_get_item(self):
        from mmap import mmap
        
        f = open(self.tmpname + "r", "w+")
        f.write("foobar")
        f.flush()
        
        m = mmap(f.fileno(), 6)
        fn = lambda: m["foo"]
        raises(TypeError, fn)
        fn = lambda: m[-7]
        raises(IndexError, fn)
        assert m[0] == 'f'
        assert m[-1] == 'r'
        # sl = slice(1, 2)
        # assert m.get_item(sl) == 'o'
        m.close()
        f.close()
    
    def test_set_item(self):
        import mmap
        
        f = open(self.tmpname + "s", "w+")
        f.write("foobar")
        f.flush()

        m = mmap.mmap(f.fileno(), 6, access=mmap.ACCESS_READ)
        def fn(): m[1] = 'a'
        raises(TypeError, fn)
        m = mmap.mmap(f.fileno(), 6, access=mmap.ACCESS_WRITE)
        def fn(): m["foo"] = 'a'
        raises(TypeError, fn)
        def fn(): m[-7] = 'a'
        raises(IndexError, fn)
        def fn(): m[0] = 'ab'
        raises((IndexError, ValueError), fn)     # IndexError is in CPython,
                                                 # but doesn't make much sense
        # def f(m): m[1:3] = u'xx'
        # py.test.raises(IndexError, f, m)
        # def f(m): m[1:4] = "zz"
        # py.test.raises(IndexError, f, m)
        # def f(m): m[1:6] = "z" * 6
        # py.test.raises(IndexError, f, m)
        # def f(m): m[:2] = "z" * 5
        # m[1:3] = 'xx'
        # assert m.read(6) == "fxxbar"
        # m.seek(0)
        m[0] = 'x'
        assert m[0] == 'x'
        m[-6] = 'y'
        data = m.read(6)
        assert data == "yoobar" # yxxbar with slice's stuff
        m.close()
        f.close()
    
    def test_del_item(self):
        from mmap import mmap
        
        f = open(self.tmpname + "t", "w+")
        f.write("foobar")
        f.flush()
        
        m = mmap(f.fileno(), 6)
        def fn(): del m["foo"]
        raises(TypeError, fn)
        # def f(m): del m[1:3]
        # py.test.raises(TypeError, f, m)
        def fn(): del m[1]
        raises(TypeError, fn)
        m.close()
        f.close()

    def test_concatenation(self):
        from mmap import mmap
        
        f = open(self.tmpname + "u", "w+")
        f.write("foobar")
        f.flush()
        
        m = mmap(f.fileno(), 6)
        def fn(): m + 1
        raises((SystemError, TypeError), fn)     # SystemError is in CPython,
        def fn(m): m += 1                        # but it doesn't make much
        raises((SystemError, TypeError), fn, m)  # sense
        def fn(): 1 + m
        raises(TypeError, fn)
        m.close()
        f.close()

    def test_repeatition(self):
        from mmap import mmap
        
        f = open(self.tmpname + "v", "w+")
        f.write("foobar")
        f.flush()
        
        m = mmap(f.fileno(), 6)
        def fn(): m * 1
        raises((SystemError, TypeError), fn)      # SystemError is in CPython,
        def fn(m): m *= 1                         # but it
        raises((SystemError, TypeError), fn, m)   # doesn't
        def fn(): 1 * m                           # make much sense
        raises(TypeError, fn)
        m.close()
        f.close()
#         
#     def test_slicing(self):
#         self.f.seek(0)
#         m = mmap(self.f.fileno(), 6)
#         assert m[-3:7] == "bar"
# 

    def test_sequence_type(self):
        from mmap import mmap
        f = open(self.tmpname + "x", "w+")
        f.write("foobar")
        f.flush()
        m = mmap(f.fileno(), 6)
        import operator
        assert operator.isSequenceType(m)
        assert not operator.isMappingType(m)

    def test_buffer(self):
        from mmap import mmap
        f = open(self.tmpname + "y", "w+")
        f.write("foobar")
        f.flush()
        m = mmap(f.fileno(), 6)
        b = buffer(m)
        assert len(b) == 6
        assert b[3] == "b"
        assert b[:] == "foobar"

    def test_all(self):
        # this is a global test, ported from test_mmap.py
        import mmap
        from mmap import PAGESIZE
        import sys
        import os
        
        filename = self.tmpname + "w"
    
        f = open(filename, "w+")
    
        # write 2 pages worth of data to the file
        f.write('\0' * PAGESIZE)
        f.write('foo')
        f.write('\0' * (PAGESIZE - 3))
        f.flush()
        m = mmap.mmap(f.fileno(), 2 * PAGESIZE)
        f.close()
    
        # sanity checks
        assert m.find("foo") == PAGESIZE
        assert len(m) == 2 * PAGESIZE
        assert m[0] == '\0'
        # assert m[0:3] == '\0\0\0'
    
        # modify the file's content
        m[0] = '3'
        # m[PAGESIZE+3:PAGESIZE+3+3] = 'bar'
    
        # check that the modification worked
        assert m[0] == '3'
        # assert m[0:3] == '3\0\0'
        # assert m[PAGESIZE-1:PAGESIZE+7] == '\0foobar\0'

        m.flush()
    
        # test seeking around
        m.seek(0,0)
        assert m.tell() == 0
        m.seek(42, 1)
        assert m.tell() == 42
        m.seek(0, 2)
        assert m.tell() == len(m)
        
        raises(ValueError, m.seek, -1)
        raises(ValueError, m.seek, 1, 2)
        raises(ValueError, m.seek, -len(m) - 1, 2)
        
        # try resizing map
        if not (("darwin" in sys.platform) or ("freebsd" in sys.platform)):
            m.resize(512)
        
            assert len(m) == 512
            raises(ValueError, m.seek, 513, 0)
            
            # check that the underlying file is truncated too
            f = open(filename)
            f.seek(0, 2)
            assert f.tell() == 512
            f.close()
            assert m.size() == 512
        
        m.close()
        f.close()
        
        # test access=ACCESS_READ
        mapsize = 10
        f = open(filename, "wb")
        f.write("a" * mapsize)
        f.close()
        f = open(filename, "rb")
        m = mmap.mmap(f.fileno(), mapsize, access=mmap.ACCESS_READ)
        # assert m[:] == 'a' * mapsize
        # def f(m): m[:] = 'b' * mapsize
        # py.test.raises(TypeError, f, m)
        def fn(): m[0] = 'b'
        raises(TypeError, fn)
        def fn(m): m.seek(0, 0); m.write("abc")
        raises(TypeError, fn, m)
        def fn(m): m.seek(0, 0); m.write_byte("d")
        raises(TypeError, fn, m)
        if not (("darwin" in sys.platform) or ("freebsd" in sys.platform)):
            raises(TypeError, m.resize, 2 * mapsize)
            assert open(filename, "rb").read() == 'a' * mapsize
        
        # opening with size too big
        f = open(filename, "r+b")
        if not os.name == "nt":
            # this should work under windows
            raises(ValueError, mmap.mmap, f.fileno(), mapsize + 1)
        f.close()
        
        # if _MS_WINDOWS:
        #     # repair damage from the resizing test.
        #     f = open(filename, 'r+b')
        #     f.truncate(mapsize)
        #     f.close()
        m.close()
        
        # test access=ACCESS_WRITE"
        f = open(filename, "r+b")
        m = mmap.mmap(f.fileno(), mapsize, access=mmap.ACCESS_WRITE)
        m.write('c' * mapsize)
        m.seek(0)
        data = m.read(mapsize)
        assert data == 'c' * mapsize
        m.flush()
        m.close()
        f.close()
        f = open(filename, 'rb')
        stuff = f.read()
        f.close()
        assert stuff == 'c' * mapsize
        
        # test access=ACCESS_COPY
        f = open(filename, "r+b")
        m = mmap.mmap(f.fileno(), mapsize, access=mmap.ACCESS_COPY)
        m.write('d' * mapsize)
        m.seek(0)
        data = m.read(mapsize)
        assert data == 'd' * mapsize
        m.flush()
        assert open(filename, "rb").read() == 'c' * mapsize
        if not (("darwin" in sys.platform) or ("freebsd" in sys.platform)):
            raises(TypeError, m.resize, 2 * mapsize)
        m.close()
        f.close()
        
        # test invalid access
        f = open(filename, "r+b")
        raises(ValueError, mmap.mmap, f.fileno(), mapsize, access=4)
        f.close()
        
        # test incompatible parameters
        if os.name == "posix":
            f = open(filename, "r+b")
            raises(ValueError, mmap.mmap, f.fileno(), mapsize, flags=mmap.MAP_PRIVATE,
                prot=mmap.PROT_READ, access=mmap.ACCESS_WRITE)
            f.close()

        
        # bad file descriptor
        raises(EnvironmentError, mmap.mmap, -2, 4096)
        
        # do a tougher .find() test.  SF bug 515943 pointed out that, in 2.2,
        # searching for data with embedded \0 bytes didn't work.
        f = open(filename, 'w+')
        data = 'aabaac\x00deef\x00\x00aa\x00'
        n = len(data)
        f.write(data)
        f.flush()
        m = mmap.mmap(f.fileno(), n)
        f.close()
        
        for start in range(n + 1):
            for finish in range(start, n + 1):
                sl = data[start:finish]
                assert m.find(sl) == data.find(sl)
                assert m.find(sl + 'x') ==  -1
        m.close()
        
        # test mapping of entire file by passing 0 for map length
        f = open(filename, "w+")
        f.write(2**16 * 'm')
        f.close()
        f = open(filename, "rb+")
        m = mmap.mmap(f.fileno(), 0)
        assert len(m) == 2**16
        assert m.read(2**16) == 2**16 * "m"
        m.close()
        f.close()
        
        # make move works everywhere (64-bit format problem earlier)
        f = open(filename, 'w+')
        f.write("ABCDEabcde")
        f.flush()
        m = mmap.mmap(f.fileno(), 10)
        m.move(5, 0, 5)
        assert m.read(10) == "ABCDEABCDE"
        m.close()
        f.close()

