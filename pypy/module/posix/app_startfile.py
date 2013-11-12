# NOT_RPYTHON

class CFFIWrapper(object):
    def __init__(self):
        import cffi
        ffi = cffi.FFI()
        ffi.cdef("""
        HINSTANCE ShellExecuteA(HWND, LPCSTR, LPCSTR, LPCSTR, LPCSTR, INT);
        HINSTANCE ShellExecuteW(HWND, LPCWSTR, LPCWSTR, LPCWSTR, LPCWSTR, INT);
        DWORD GetLastError(void);
        """)
        self.NULL = ffi.NULL
        self.cast = ffi.cast
        self.libK = ffi.dlopen("Kernel32.dll")
        self.libS = ffi.dlopen("Shell32.dll")
        self.SW_SHOWNORMAL = 1

_cffi_wrapper = None


def startfile(filepath, operation=None):
    global _cffi_wrapper
    if _cffi_wrapper is None:
        _cffi_wrapper = CFFIWrapper()
    w = _cffi_wrapper
    #
    if operation is None:
        operation = w.NULL
    if isinstance(filepath, str):
        if isinstance(operation, unicode):
            operation = operation.encode("ascii")
        rc = w.libS.ShellExecuteA(w.NULL, operation, filepath,
                                  w.NULL, w.NULL, w.SW_SHOWNORMAL)
    elif isinstance(filepath, unicode):
        if isinstance(operation, str):
            operation = operation.decode("ascii")
        rc = w.libS.ShellExecuteW(w.NULL, operation, filepath,
                                  w.NULL, w.NULL, w.SW_SHOWNORMAL)
    else:
        raise TypeError("argument 1 must be str or unicode")
    rc = int(w.cast("uintptr_t", rc))
    if rc <= 32:
        # sorry, no way to get the error message in less than one page of code
        code = w.libK.GetLastError()
        raise WindowsError(code, "Error %s" % code, filepath)
