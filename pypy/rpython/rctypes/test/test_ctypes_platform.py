import py, sys, struct
from pypy.rpython.rctypes import ctypes_platform
import ctypes


if sys.platform != 'linux2':
    py.test.skip("the test must be adapted to your platform")


def test_dirent():
    dirent = ctypes_platform.getstruct("struct dirent",
                                       """
           struct dirent  /* for this example only, not the exact dirent */
           {
               long d_ino;
               int d_off;
               unsigned short d_reclen;
               char d_name[32];
           };
                                       """,
                                       [("d_reclen", ctypes.c_ushort)])
    assert issubclass(dirent, ctypes.Structure)
    ssize = (ctypes.sizeof(ctypes.c_long) +
             ctypes.sizeof(ctypes.c_int) +
             ctypes.sizeof(ctypes.c_ushort) +
             32)
    extra_padding = (-ssize) % ctypes.alignment(ctypes.c_long)

    assert dirent._fields_ == [('_alignment', ctypes.c_long),
                               ('_pad0', ctypes.c_char),
                               ('_pad1', ctypes.c_char),
                               ('_pad2', ctypes.c_char),
                               ('_pad3', ctypes.c_char),
                               ('d_reclen', ctypes.c_ushort),
                               ] + [
                               ('_pad%d' % n, ctypes.c_char)
                                    for n in range(4, 4+32+extra_padding)]
    assert ctypes.sizeof(dirent) == ssize + extra_padding
    assert ctypes.alignment(dirent) == ctypes.alignment(ctypes.c_long)

def test_fit_type():
    S = ctypes_platform.getstruct("struct S",
                                  """
           struct S {
               signed char c;
               unsigned char uc;
               short s;
               unsigned short us;
               int i;
               unsigned int ui;
               long l;
               unsigned long ul;
               long long ll;
               unsigned long long ull;
               float f;
               double d;
           };
                                  """,
                                  [("c",   ctypes.c_int),
                                   ("uc",  ctypes.c_int),
                                   ("s",   ctypes.c_uint),
                                   ("us",  ctypes.c_int),
                                   ("i",   ctypes.c_int),
                                   ("ui",  ctypes.c_int),
                                   ("l",   ctypes.c_int),
                                   ("ul",  ctypes.c_int),
                                   ("ll",  ctypes.c_int),
                                   ("ull", ctypes.c_int),
                                   ("f",   ctypes.c_double),
                                   ("d",   ctypes.c_float)])
    assert issubclass(S, ctypes.Structure)
    fields = dict(S._fields_)
    assert fields["c"] == ctypes.c_byte
    assert fields["uc"] == ctypes.c_ubyte
    assert fields["s"] == ctypes.c_short
    assert fields["us"] == ctypes.c_ushort
    assert fields["i"] == ctypes.c_int
    assert fields["ui"] == ctypes.c_uint
    assert fields["l"] == ctypes.c_long
    assert fields["ul"] == ctypes.c_ulong
    assert fields["ll"] == ctypes.c_longlong
    assert fields["ull"] == ctypes.c_ulonglong
    assert fields["f"] == ctypes.c_float
    assert fields["d"] == ctypes.c_double

def test_simple_type():
    ctype = ctypes_platform.getsimpletype('test_t',
                                          'typedef unsigned short test_t;',
                                          ctypes.c_int)
    assert ctype == ctypes.c_ushort
