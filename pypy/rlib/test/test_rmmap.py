from pypy.tool.udir import udir
import os
from pypy.rpython.test.test_llinterp import interpret
from pypy.rlib import rmmap as mmap
from pypy.rlib.rmmap import RTypeError, RValueError, alloc, free
import sys

class TestMMap:
    def setup_class(cls):
        cls.tmpname = str(udir.join('mmap-'))
    
    def test_page_size(self):
        def f():
            assert mmap.PAGESIZE > 0
            assert isinstance(mmap.PAGESIZE, int)

        interpret(f, [])
    
    def test_attributes(self):
        def f():
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

        interpret(f, [])

    def test_file_size(self):
        if os.name == "nt":
            skip("Only Unix checks file size")
        def func(no):

            try:
                mmap.mmap(no, 123)
            except RValueError:
                pass
            else:
                raise Exception("didn't raise")

        f = open(self.tmpname + "a", "w+")
        
        f.write("c")
        f.flush()

        interpret(func, [f.fileno()])
        f.close()

    def test_create(self):
        f = open(self.tmpname + "b", "w+")
        
        f.write("c")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 1)
            assert m.read(99) == "c"

        interpret(func, [f.fileno()])
        
        f.close()

    def test_close(self):
        f = open(self.tmpname + "c", "w+")
        
        f.write("c")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 1)
            m.close()
            try:
                m.read(1)
            except RValueError:
                pass
            else:
                raise Exception("Did not raise")
        interpret(func, [f.fileno()])

    def test_read_byte(self):
        f = open(self.tmpname + "d", "w+")

        f.write("c")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 1)
            assert m.read_byte() == "c"
            try:
                m.read_byte()
            except RValueError:
                pass
            else:
                raise Exception("Did not raise")
            m.close()
        interpret(func, [f.fileno()])
        f.close()

    def test_readline(self):
        import os
        f = open(self.tmpname + "e", "w+")

        f.write("foo\n")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 4)
            if os.name == "nt":
                # windows replaces \n with \r. it's time to change to \n only MS!
                assert m.readline() == "foo\r"
            elif os.name == "posix":
                assert m.readline() == "foo\n"
            assert m.readline() == ""
            m.close()

        interpret(func, [f.fileno()])
        f.close()

    def test_read(self):
        f = open(self.tmpname + "f", "w+")
        
        f.write("foobar")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 6)
            assert m.read(1) == "f"
            assert m.read(6) == "oobar"
            assert m.read(1) == ""
            m.close()

        interpret(func, [f.fileno()])
        f.close()

    def test_find(self):
        f = open(self.tmpname + "g", "w+")

        f.write("foobar\0")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 7)
            assert m.find("b") == 3
            assert m.find("z") == -1
            assert m.find("o", 5) == -1
            assert m.find("ob") == 2
            assert m.find("\0") == 6
            m.close()

        interpret(func, [f.fileno()])
        f.close()

    def test_is_modifiable(self):
        f = open(self.tmpname + "h", "w+")
        
        f.write("foobar")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 6, access=mmap.ACCESS_READ)
            try:
                m.write('x')
            except RTypeError:
                pass
            else:
                assert False
            try:
                m.resize(7)
            except RTypeError:
                pass
            else:
                assert False
            m.close()
        interpret(func, [f.fileno()])
        f.close()

    def test_seek(self):
        f = open(self.tmpname + "i", "w+")
        
        f.write("foobar")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 6)
            m.seek(0)
            assert m.tell() == 0
            m.read(1)
            m.seek(1, 1)
            assert m.tell() == 2
            m.seek(0)
            m.seek(-1, 2)
            assert m.tell() == 5
            m.close()
        interpret(func, [f.fileno()])
        f.close()

    def test_write(self):
        f = open(self.tmpname + "j", "w+")

        f.write("foobar")
        f.flush()
        def func(no):
            m = mmap.mmap(no, 6, access=mmap.ACCESS_WRITE)
            m.write("ciao\n")
            m.seek(0)
            assert m.read(6) == "ciao\nr"
            m.close()
        interpret(func, [f.fileno()])
        f.close()

    def test_write_byte(self):
        f = open(self.tmpname + "k", "w+")
        
        f.write("foobar")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 6, access=mmap.ACCESS_READ)
            m = mmap.mmap(no, 6, access=mmap.ACCESS_WRITE)
            m.write_byte("x")
            m.seek(0)
            assert m.read(6) == "xoobar"
            m.close()
        interpret(func, [f.fileno()])
        f.close()

    def test_size(self):
        f = open(self.tmpname + "l", "w+")
        
        f.write("foobar")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 5)
            assert m.file_size() == 6 # size of the underline file, not the mmap
            m.close()

        interpret(func, [f.fileno()])
        f.close()

    def test_tell(self):
        f = open(self.tmpname + "m", "w+")
        
        f.write("c")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 1)
            assert m.tell() >= 0
            m.close()

        interpret(func, [f.fileno()])
        f.close()

    def test_move(self):
        f = open(self.tmpname + "o", "w+")
        
        f.write("foobar")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 6, access=mmap.ACCESS_WRITE)
            m.move(1, 3, 3)
            assert m.read(6) == "fbarar"
            m.seek(0)
            m.move(1, 3, 2)
            a = m.read(6)
            assert a == "frarar"
            m.close()

        interpret(func, [f.fileno()])
        f.close()
    
    def test_resize(self):
        import sys
        if ("darwin" in sys.platform) or ("freebsd" in sys.platform):
            skip("resize does not work under OSX or FreeBSD")
        
        import os
        
        f = open(self.tmpname + "p", "w+")
        f.write("foobar")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 6, access=mmap.ACCESS_WRITE)
            f_size = os.fstat(no).st_size
            assert m.file_size() == f_size == 6
            m.resize(10)
            f_size = os.fstat(no).st_size
            assert m.file_size() == f_size == 10
            m.close()

        interpret(func, [f.fileno()])
        f.close()

    def test_len(self):
        
        f = open(self.tmpname + "q", "w+")
        f.write("foobar")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 6)
            assert m.len() == 6
            m.close()

        interpret(func, [f.fileno()])
        f.close()
     
    def test_get_item(self):
        
        f = open(self.tmpname + "r", "w+")
        f.write("foobar")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 6)
            assert m.getitem(0) == 'f'
            assert m.getitem(-1) == 'r'
        # sl = slice(1, 2)
        # assert m.get_item(sl) == 'o'
            m.close()

        interpret(func, [f.fileno()])
        f.close()
    
    def test_set_item(self):
        f = open(self.tmpname + "s", "w+")
        f.write("foobar")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 6, access=mmap.ACCESS_WRITE)

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
            m.setitem(0, 'x')
            assert m.getitem(0) == 'x'
            m.setitem(-6, 'y')
            data = m.read(6)
            assert data == "yoobar" # yxxbar with slice's stuff
            m.close()

        interpret(func, [f.fileno()])
        f.close()

    def test_double_close(self):
        f = open(self.tmpname + "s", "w+")
        f.write("foobar")
        f.flush()

        def func(no):
            m = mmap.mmap(no, 6, access=mmap.ACCESS_WRITE)
            m.close()
            m.close() # didn't explode

        interpret(func, [f.fileno()])
        f.close()

    def test_translated(self):
        from pypy.translator.c.test.test_genc import compile

        def func(no):
            m = mmap.mmap(no, 1)
            r = m.read_byte()
            m.close()
            return r

        compile(func, [int])

def test_alloc_free():
    map_size = 65536
    data = alloc(map_size)
    for i in range(0, map_size, 171):
        data[i] = chr(i & 0xff)
    for i in range(0, map_size, 171):
        assert data[i] == chr(i & 0xff)
    free(data, map_size)

def test_compile_alloc_free():
    from pypy.translator.c.test.test_genc import compile

    fn = compile(test_alloc_free, [])
    fn()
