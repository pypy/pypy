"""
Test the compilation of the mmap mixedmodule to a CPython extension
module.
"""

from pypy.interpreter.mixedmodule import testmodule, compilemodule
from pypy.tool.udir import udir
import sys
import os


def test_cpy():
    run_tests(testmodule("mmap"))

def test_compiled():
    run_tests(compilemodule("mmap"))


def run_tests(mmap):
    # this is a global test, ported from test_mmap.py
    PAGESIZE = mmap.PAGESIZE

    filename = str(udir.join('mmap-mixedmodule'))

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
    open(filename, "wb").write("a" * mapsize)
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
