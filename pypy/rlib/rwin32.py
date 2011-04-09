""" External functions accessing the win32 api.
Common types, functions from core win32 libraries, such as kernel32
"""

from pypy.rpython.tool import rffi_platform
from pypy.tool.udir import udir
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import CompilationError
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import intmask
from pypy.rlib import jit
import os, sys, errno

# This module can be imported on any platform,
# but most symbols are not usable...
WIN32 = os.name == "nt"

if WIN32:
    eci = ExternalCompilationInfo(
        includes = ['windows.h'],
        libraries = ['kernel32'],
        )
else:
    eci = ExternalCompilationInfo()

class CConfig:
    _compilation_info_ = eci

    if WIN32:
        DWORD_PTR = rffi_platform.SimpleType("DWORD_PTR", rffi.LONG)
        WORD = rffi_platform.SimpleType("WORD", rffi.UINT)
        DWORD = rffi_platform.SimpleType("DWORD", rffi.UINT)
        BOOL = rffi_platform.SimpleType("BOOL", rffi.LONG)
        BYTE = rffi_platform.SimpleType("BYTE", rffi.UCHAR)
        WCHAR = rffi_platform.SimpleType("WCHAR", rffi.UCHAR)
        INT = rffi_platform.SimpleType("INT", rffi.INT)
        LONG = rffi_platform.SimpleType("LONG", rffi.LONG)
        PLONG = rffi_platform.SimpleType("PLONG", rffi.LONGP)
        LPVOID = rffi_platform.SimpleType("LPVOID", rffi.INTP)
        LPCVOID = rffi_platform.SimpleType("LPCVOID", rffi.VOIDP)
        LPSTR = rffi_platform.SimpleType("LPSTR", rffi.CCHARP)
        LPCSTR = rffi_platform.SimpleType("LPCSTR", rffi.CCHARP)
        LPWSTR = rffi_platform.SimpleType("LPWSTR", rffi.CWCHARP)
        LPCWSTR = rffi_platform.SimpleType("LPCWSTR", rffi.CWCHARP)
        LPDWORD = rffi_platform.SimpleType("LPDWORD", rffi.UINTP)
        SIZE_T = rffi_platform.SimpleType("SIZE_T", rffi.SIZE_T)
        ULONG_PTR = rffi_platform.SimpleType("ULONG_PTR", rffi.ULONG)

        HRESULT = rffi_platform.SimpleType("HRESULT", rffi.LONG)
        HLOCAL = rffi_platform.SimpleType("HLOCAL", rffi.VOIDP)

        FILETIME = rffi_platform.Struct('FILETIME',
                                        [('dwLowDateTime', rffi.UINT),
                                         ('dwHighDateTime', rffi.UINT)])
        SYSTEMTIME = rffi_platform.Struct('SYSTEMTIME',
                                          [])

        OSVERSIONINFO = rffi_platform.Struct(
            'OSVERSIONINFO',
            [('dwOSVersionInfoSize', rffi.UINT),
             ('dwMajorVersion', rffi.UINT),
             ('dwMinorVersion', rffi.UINT),
             ('dwBuildNumber',  rffi.UINT),
             ('dwPlatformId',  rffi.UINT),
             ('szCSDVersion', rffi.CFixedArray(lltype.Char, 1))])

        LPSECURITY_ATTRIBUTES = rffi_platform.SimpleType(
            "LPSECURITY_ATTRIBUTES", rffi.CCHARP)

        DEFAULT_LANGUAGE = rffi_platform.ConstantInteger(
            "MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT)")

        for name in """FORMAT_MESSAGE_ALLOCATE_BUFFER FORMAT_MESSAGE_FROM_SYSTEM
                       MAX_PATH
                       WAIT_OBJECT_0 WAIT_TIMEOUT INFINITE
                    """.split():
            locals()[name] = rffi_platform.ConstantInteger(name)

for k, v in rffi_platform.configure(CConfig).items():
    globals()[k] = v

def winexternal(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci, calling_conv='win')

if WIN32:
    HANDLE = rffi.COpaquePtr(typedef='HANDLE')
    assert rffi.cast(HANDLE, -1) == rffi.cast(HANDLE, -1)

    LPHANDLE = rffi.CArrayPtr(HANDLE)
    HMODULE = HANDLE
    NULL_HANDLE = rffi.cast(HANDLE, 0)
    INVALID_HANDLE_VALUE = rffi.cast(HANDLE, -1)
    PFILETIME = rffi.CArrayPtr(FILETIME)

    GetLastError = winexternal('GetLastError', [], DWORD)
    SetLastError = winexternal('SetLastError', [DWORD], lltype.Void)

    # In tests, the first call to GetLastError is always wrong, because error
    # is hidden by operations in ll2ctypes.  Call it now.
    GetLastError()

    LoadLibrary = winexternal('LoadLibraryA', [rffi.CCHARP], HMODULE)
    GetProcAddress = winexternal('GetProcAddress',
                                 [HMODULE, rffi.CCHARP],
                                 rffi.VOIDP)
    FreeLibrary = winexternal('FreeLibrary', [HMODULE], BOOL)

    LocalFree = winexternal('LocalFree', [HLOCAL], DWORD)
    CloseHandle = winexternal('CloseHandle', [HANDLE], BOOL)

    FormatMessage = winexternal(
        'FormatMessageA',
        [DWORD, rffi.VOIDP, DWORD, DWORD, rffi.CCHARP, DWORD, rffi.VOIDP],
        DWORD)

    _get_osfhandle = rffi.llexternal('_get_osfhandle', [rffi.INT], HANDLE)

    def build_winerror_to_errno():
        """Build a dictionary mapping windows error numbers to POSIX errno.
        The function returns the dict, and the default value for codes not
        in the dict."""
        # Prior to Visual Studio 8, the MSVCRT dll doesn't export the
        # _dosmaperr() function, which is available only when compiled
        # against the static CRT library.
        from pypy.translator.platform import platform, Windows
        static_platform = Windows()
        if static_platform.name == 'msvc':
            static_platform.cflags = ['/MT']  # static CRT
            static_platform.version = 0       # no manifest
        cfile = udir.join('dosmaperr.c')
        cfile.write(r'''
                #include <errno.h>
                int main()
                {
                    int i;
                    for(i=1; i < 65000; i++) {
                        _dosmaperr(i);
                        if (errno == EINVAL)
                            continue;
                        printf("%d\t%d\n", i, errno);
                    }
                    return 0;
                }''')
        try:
            exename = static_platform.compile(
                [cfile], ExternalCompilationInfo(),
                outputfilename = "dosmaperr",
                standalone=True)
        except (CompilationError, WindowsError):
            # Fallback for the mingw32 compiler
            errors = {
                2: 2, 3: 2, 4: 24, 5: 13, 6: 9, 7: 12, 8: 12, 9: 12, 10: 7,
                11: 8, 15: 2, 16: 13, 17: 18, 18: 2, 19: 13, 20: 13, 21: 13,
                22: 13, 23: 13, 24: 13, 25: 13, 26: 13, 27: 13, 28: 13,
                29: 13, 30: 13, 31: 13, 32: 13, 33: 13, 34: 13, 35: 13,
                36: 13, 53: 2, 65: 13, 67: 2, 80: 17, 82: 13, 83: 13, 89: 11,
                108: 13, 109: 32, 112: 28, 114: 9, 128: 10, 129: 10, 130: 9,
                132: 13, 145: 41, 158: 13, 161: 2, 164: 11, 167: 13, 183: 17,
                188: 8, 189: 8, 190: 8, 191: 8, 192: 8, 193: 8, 194: 8,
                195: 8, 196: 8, 197: 8, 198: 8, 199: 8, 200: 8, 201: 8,
                202: 8, 206: 2, 215: 11, 1816: 12,
                }
        else:
            output = os.popen(str(exename))
            errors = dict(map(int, line.split())
                          for line in output)
        return errors, errno.EINVAL

    # A bit like strerror...
    def FormatError(code):
        return llimpl_FormatError(code)

    def llimpl_FormatError(code):
        "Return a message corresponding to the given Windows error code."
        buf = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')

        try:
            msglen = FormatMessage(FORMAT_MESSAGE_ALLOCATE_BUFFER |
                                   FORMAT_MESSAGE_FROM_SYSTEM,
                                   None,
                                   code,
                                   DEFAULT_LANGUAGE,
                                   rffi.cast(rffi.CCHARP, buf),
                                   0, None)

            if msglen <= 2 or msglen > sys.maxint:
                return fake_FormatError(code)

            # FormatMessage always appends \r\n.
            buflen = intmask(msglen - 2)
            assert buflen > 0

            result = rffi.charpsize2str(buf[0], buflen)
            LocalFree(rffi.cast(rffi.VOIDP, buf[0]))
        finally:
            lltype.free(buf, flavor='raw')

        return result

    def fake_FormatError(code):
        return 'Windows Error %d' % (code,)

    def lastWindowsError(context="Windows Error"):
        code = GetLastError()
        return WindowsError(code, context)

    def FAILED(hr):
        return rffi.cast(HRESULT, hr) < 0

    _GetModuleFileName = winexternal('GetModuleFileNameA',
                                     [HMODULE, rffi.CCHARP, DWORD],
                                     DWORD)

    def GetModuleFileName(module):
        size = MAX_PATH
        buf = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw')
        try:
            res = _GetModuleFileName(module, buf, size)
            if not res:
                return ''
            else:
                return ''.join([buf[i] for i in range(res)])
        finally:
            lltype.free(buf, flavor='raw')

    _GetVersionEx = winexternal('GetVersionExA',
                                [lltype.Ptr(OSVERSIONINFO)],
                                DWORD)

    @jit.dont_look_inside
    def GetVersionEx():
        info = lltype.malloc(OSVERSIONINFO, flavor='raw')
        rffi.setintfield(info, 'c_dwOSVersionInfoSize',
                         rffi.sizeof(OSVERSIONINFO))
        try:
            if not _GetVersionEx(info):
                raise lastWindowsError()
            return (rffi.cast(lltype.Signed, info.c_dwMajorVersion),
                    rffi.cast(lltype.Signed, info.c_dwMinorVersion),
                    rffi.cast(lltype.Signed, info.c_dwBuildNumber),
                    rffi.cast(lltype.Signed, info.c_dwPlatformId),
                    rffi.charp2str(rffi.cast(rffi.CCHARP,
                                             info.c_szCSDVersion)))
        finally:
            lltype.free(info, flavor='raw')

    _WaitForSingleObject = winexternal(
        'WaitForSingleObject', [HANDLE, DWORD], DWORD)

    def WaitForSingleObject(handle, timeout):
        """Return values:
        - WAIT_OBJECT_0 when the object is signaled
        - WAIT_TIMEOUT when the timeout elapsed"""
        res = _WaitForSingleObject(handle, timeout)
        if res == rffi.cast(DWORD, -1):
            raise lastWindowsError("WaitForSingleObject")
        return res

    _WaitForMultipleObjects = winexternal(
        'WaitForMultipleObjects', [
            DWORD, rffi.CArrayPtr(HANDLE), BOOL, DWORD], DWORD)

    def WaitForMultipleObjects(handles, waitall=False, timeout=INFINITE):
        """Return values:
        - WAIT_OBJECT_0 + index when an object is signaled
        - WAIT_TIMEOUT when the timeout elapsed"""
        nb = len(handles)
        handle_array = lltype.malloc(rffi.CArrayPtr(HANDLE).TO, nb,
                                     flavor='raw')
        try:
            for i in range(nb):
                handle_array[i] = handles[i]
            res = _WaitForMultipleObjects(nb, handle_array, waitall, timeout)
            if res == rffi.cast(DWORD, -1):
                raise lastWindowsError("WaitForMultipleObjects")
            return res
        finally:
            lltype.free(handle_array, flavor='raw')

    _CreateEvent = winexternal(
        'CreateEventA', [rffi.VOIDP, BOOL, BOOL, LPCSTR], HANDLE)
    def CreateEvent(*args):
        handle = _CreateEvent(*args)
        if handle == NULL_HANDLE:
            raise lastWindowsError("CreateEvent")
        return handle
    SetEvent = winexternal(
        'SetEvent', [HANDLE], BOOL)
    ResetEvent = winexternal(
        'ResetEvent', [HANDLE], BOOL)

