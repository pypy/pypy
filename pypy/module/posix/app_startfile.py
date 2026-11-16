# NOT_RPYTHON

class CFFIWrapper(object):
    def __init__(self):
        import cffi
        ffi = cffi.FFI()
        ffi.cdef("""
        HINSTANCE ShellExecuteA(HWND, LPCSTR, LPCSTR, LPCSTR, LPCSTR, INT);
        HINSTANCE ShellExecuteW(HWND, LPCWSTR, LPCWSTR, LPCWSTR, LPCWSTR, INT);
        """)
        self.NULL = ffi.NULL
        self.cast = ffi.cast
        self.lib = ffi.dlopen("Shell32.dll")
        self.getwinerror = ffi.getwinerror

_cffi_wrapper = None


def _as_bytes(w, arg):
    if arg is None:
        return w.NULL
    if isinstance(arg, str):
        return arg.encode("ascii")
    return arg


def _as_str(w, arg):
    if arg is None:
        return w.NULL
    if isinstance(arg, bytes):
        return arg.decode("ascii")
    return arg


def startfile(filepath, operation=None, arguments=None, cwd=None, show_cmd=1):
    global _cffi_wrapper
    if _cffi_wrapper is None:
        _cffi_wrapper = CFFIWrapper()
    w = _cffi_wrapper
    #
    if isinstance(filepath, bytes):
        rc = w.lib.ShellExecuteA(w.NULL, _as_bytes(w, operation), filepath,
                                 _as_bytes(w, arguments),
                                 _as_bytes(w, cwd), show_cmd)
    elif isinstance(filepath, str):
        rc = w.lib.ShellExecuteW(w.NULL, _as_str(w, operation), filepath,
                                 _as_str(w, arguments),
                                 _as_str(w, cwd), show_cmd)
    else:
        raise TypeError("argument 1 must be str or bytes")
    rc = int(w.cast("uintptr_t", rc))
    if rc <= 32:
        code, msg = w.getwinerror()
        raise WindowsError(code, msg, filepath)
