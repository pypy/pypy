""" External functions accessing the win32 api.
Common types, functions from core win32 libraries, such as kernel32
"""

from pypy.rpython.tool import rffi_platform
from pypy.tool.udir import udir
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import intmask
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
        INT = rffi_platform.SimpleType("INT", rffi.INT)
        LONG = rffi_platform.SimpleType("LONG", rffi.LONG)
        PLONG = rffi_platform.SimpleType("PLONG", rffi.LONGP)
        LPVOID = rffi_platform.SimpleType("LPVOID", rffi.INTP)
        LPCVOID = rffi_platform.SimpleType("LPCVOID", rffi.VOIDP)
        LPSTR = rffi_platform.SimpleType("LPSTR", rffi.CCHARP)
        LPCSTR = rffi_platform.SimpleType("LPCSTR", rffi.CCHARP)
        LPDWORD = rffi_platform.SimpleType("LPDWORD", rffi.INTP)
        SIZE_T = rffi_platform.SimpleType("SIZE_T", rffi.SIZE_T)
        ULONG_PTR = rffi_platform.SimpleType("ULONG_PTR", rffi.ULONG)

        HRESULT = rffi_platform.SimpleType("HRESULT", rffi.LONG)
        HLOCAL = rffi_platform.SimpleType("HLOCAL", rffi.VOIDP)

        FILETIME = rffi_platform.Struct('FILETIME',
                                        [('dwLowDateTime', rffi.UINT),
                                         ('dwHighDateTime', rffi.UINT)])
        SYSTEMTIME = rffi_platform.Struct('SYSTEMTIME',
                                          [])

        LPSECURITY_ATTRIBUTES = rffi_platform.SimpleType(
            "LPSECURITY_ATTRIBUTES", rffi.CCHARP)

        DEFAULT_LANGUAGE = rffi_platform.ConstantInteger(
            "MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT)")

        for name in """FORMAT_MESSAGE_ALLOCATE_BUFFER FORMAT_MESSAGE_FROM_SYSTEM
                       MAX_PATH
                    """.split():
            locals()[name] = rffi_platform.ConstantInteger(name)

for k, v in rffi_platform.configure(CConfig).items():
    globals()[k] = v

def winexternal(name, args, result):
    return rffi.llexternal(name, args, result, compilation_info=eci, calling_conv='win')

if WIN32:
    HANDLE = rffi.ULONG
    LPHANDLE = rffi.CArrayPtr(HANDLE)
    HMODULE = HANDLE
    INVALID_HANDLE_VALUE = rffi.cast(HANDLE, -1)
    PFILETIME = rffi.CArrayPtr(FILETIME)

    GetLastError = winexternal('GetLastError', [], DWORD)
    SetLastError = winexternal('SetLastError', [DWORD], lltype.Void)

    LoadLibrary = winexternal('LoadLibraryA', [rffi.CCHARP], rffi.VOIDP)
    GetProcAddress = winexternal('GetProcAddress',
                                 [rffi.VOIDP, rffi.CCHARP],
                                 rffi.VOIDP)
    FreeLibrary = winexternal('FreeLibrary', [rffi.VOIDP], BOOL)

    LocalFree = winexternal('LocalFree', [HLOCAL], DWORD)
    CloseHandle = winexternal('CloseHandle', [HANDLE], lltype.Void)

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
        exename = static_platform.compile(
            [cfile], ExternalCompilationInfo(),
            outputfilename = "dosmaperr",
            standalone=True)
        output = os.popen(str(exename))
        errors = dict(map(int, line.split())
                      for line in output)
        return errors, errno.EINVAL

    # A bit like strerror...
    def FormatError(code):
        return llimpl_FormatError(code)

    def llimpl_FormatError(code):
        "Return a message corresponding to the given Windows error code."
        buf = lltype.malloc(rffi.VOIDPP.TO, 1, flavor='raw')

        try:
            msglen = FormatMessage(FORMAT_MESSAGE_ALLOCATE_BUFFER |
                                   FORMAT_MESSAGE_FROM_SYSTEM,
                                   None,
                                   code,
                                   DEFAULT_LANGUAGE,
                                   rffi.cast(rffi.VOIDP, buf),
                                   0, None)

            if msglen <= 2 or msglen > sys.maxint:
                return fake_FormatError(code)

            # FormatMessage always appends \r\n.
            buflen = intmask(msglen - 2)
            assert buflen > 0

            result = rffi.charpsize2str(buf[0], buflen)
            LocalFree(buf[0])
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
