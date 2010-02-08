import py
import sys, os, unittest
from ctypes import *

try:
    WINFUNCTYPE
except NameError:
    # fake to enable this test on Linux
    WINFUNCTYPE = CFUNCTYPE

def setup_module(mod):
    import conftest
    _ctypes_test = str(conftest.sofile)
    mod.lib = CDLL(_ctypes_test)


class TestCFuncPtr:
    def test_basic(self):
        X = WINFUNCTYPE(c_int, c_int, c_int)

        def func(*args):
            return len(args)

        x = X(func)
        assert x.restype == c_int
        assert x.argtypes == (c_int, c_int)
        assert sizeof(x) == sizeof(c_voidp)
        assert sizeof(X) == sizeof(c_voidp)

    def test_first(self):
        StdCallback = WINFUNCTYPE(c_int, c_int, c_int)
        CdeclCallback = CFUNCTYPE(c_int, c_int, c_int)

        def func(a, b):
            return a + b

        s = StdCallback(func)
        c = CdeclCallback(func)

        assert s(1, 2) == 3
        assert c(1, 2) == 3
        # The following no longer raises a TypeError - it is now
        # possible, as in C, to call cdecl functions with more parameters.
        #self.assertRaises(TypeError, c, 1, 2, 3)
        py.test.skip("cdecl funcptrs ignoring extra args is not implemented")
        assert c(1, 2, 3, 4, 5, 6) == 3
        if not WINFUNCTYPE is CFUNCTYPE and os.name != "ce":
            raises(TypeError, s, 1, 2, 3)

    def test_structures(self):
        if sys.platform != 'win32':
            py.test.skip("win32 related")
        WNDPROC = WINFUNCTYPE(c_long, c_int, c_int, c_int, c_int)

        def wndproc(hwnd, msg, wParam, lParam):
            return hwnd + msg + wParam + lParam

        HINSTANCE = c_int
        HICON = c_int
        HCURSOR = c_int
        LPCTSTR = c_char_p

        class WNDCLASS(Structure):
            _fields_ = [("style", c_uint),
                        ("lpfnWndProc", WNDPROC),
                        ("cbClsExtra", c_int),
                        ("cbWndExtra", c_int),
                        ("hInstance", HINSTANCE),
                        ("hIcon", HICON),
                        ("hCursor", HCURSOR),
                        ("lpszMenuName", LPCTSTR),
                        ("lpszClassName", LPCTSTR)]

        wndclass = WNDCLASS()
        wndclass.lpfnWndProc = WNDPROC(wndproc)

        WNDPROC_2 = WINFUNCTYPE(c_long, c_int, c_int, c_int, c_int)

        # This is no longer true, now that WINFUNCTYPE caches created types internally.
        ## # CFuncPtr subclasses are compared by identity, so this raises a TypeError:
        ## raises(TypeError, setattr, wndclass,
        ##                  "lpfnWndProc", WNDPROC_2(wndproc))
        # instead:

        assert WNDPROC is WNDPROC_2
        # 'wndclass.lpfnWndProc' leaks 94 references.  Why?
        assert wndclass.lpfnWndProc(1, 2, 3, 4) == 10


        f = wndclass.lpfnWndProc

        del wndclass
        del wndproc

        assert f(10, 11, 12, 13) == 46

    def test_dllfunctions(self):

        def NoNullHandle(value):
            if not value:
                raise WinError()
            return value

        strchr = lib.my_strchr
        strchr.restype = c_char_p
        strchr.argtypes = (c_char_p, c_char)
        assert strchr("abcdefghi", "b") == "bcdefghi"
        assert strchr("abcdefghi", "x") == None


        strtok = lib.my_strtok
        strtok.restype = c_char_p
        # Neither of this does work: strtok changes the buffer it is passed
##        strtok.argtypes = (c_char_p, c_char_p)
##        strtok.argtypes = (c_string, c_char_p)

        def c_string(init):
            size = len(init) + 1
            return (c_char*size)(*init)

        s = "a\nb\nc"
        b = c_string(s)

##        b = (c_char * (len(s)+1))()
##        b.value = s

##        b = c_string(s)
        assert strtok(b, "\n") == "a"
        assert strtok(None, "\n") == "b"
        assert strtok(None, "\n") == "c"
        assert strtok(None, "\n") == None

    def test_from_address(self):
        def make_function():
            proto = CFUNCTYPE(c_int)
            a=create_string_buffer(
                "\xB8\x78\x56\x34\x12" # mov eax, 0x12345678
                "\xc3"                 # ret 0
                )
            ptr = pointer(a)
            func = proto.from_address(addressof(ptr))
            func.__keep = ptr # keep ptr alive
            return func
        f = make_function()
        # This assembler should also work on Linux 32bit,
        # but it segfaults for some reason.
        if sys.platform == 'win32':
            assert f() == 0x12345678
