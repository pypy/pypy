""" External functions accessing the win32 api.
Common types, functions from core win32 libraries, such as kernel32
"""

from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import lltype, rffi
import os

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
        INT = rffi_platform.SimpleType("INT", rffi.INT)
        LONG = rffi_platform.SimpleType("LONG", rffi.LONG)
        PLONG = rffi_platform.SimpleType("PLONG", rffi.LONGP)
        LPVOID = rffi_platform.SimpleType("LPVOID", rffi.INTP)
        LPCVOID = rffi_platform.SimpleType("LPCVOID", rffi.VOIDP)
        LPCTSTR = rffi_platform.SimpleType("LPCTSTR", rffi.CCHARP)
        LPDWORD = rffi_platform.SimpleType("LPDWORD", rffi.INTP)
        SIZE_T = rffi_platform.SimpleType("SIZE_T", rffi.SIZE_T)

        HRESULT = rffi_platform.SimpleType("HRESULT", rffi.LONG)
        HLOCAL = rffi_platform.SimpleType("HLOCAL", rffi.VOIDP)

        DEFAULT_LANGUAGE = rffi_platform.ConstantInteger(
            "MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT)")

        for name in """FORMAT_MESSAGE_ALLOCATE_BUFFER FORMAT_MESSAGE_FROM_SYSTEM
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

    GetLastError = winexternal('GetLastError', [], DWORD)

    LoadLibrary = winexternal('LoadLibraryA', [rffi.CCHARP], rffi.VOIDP)
    GetProcAddress = winexternal('GetProcAddress',
                                 [rffi.VOIDP, rffi.CCHARP],
                                 rffi.VOIDP)
    FreeLibrary = winexternal('FreeLibrary', [rffi.VOIDP], BOOL)

    LocalFree = winexternal('LocalFree', [HLOCAL], DWORD)

    FormatMessage = winexternal(
        'FormatMessageA',
        [DWORD, rffi.VOIDP, DWORD, DWORD, rffi.CCHARP, DWORD, rffi.VOIDP],
        DWORD)


    # A bit like strerror...
    def FormatError(code):
        "Return a message corresponding to the given Windows error code."
        buf = lltype.malloc(rffi.VOIDPP.TO, 1, flavor='raw')

        msglen = FormatMessage(FORMAT_MESSAGE_ALLOCATE_BUFFER |
                               FORMAT_MESSAGE_FROM_SYSTEM,
                               None,
                               code,
                               DEFAULT_LANGUAGE,
                               rffi.cast(rffi.VOIDP, buf),
                               0, None)

        # FormatMessage always appends a \n.
        msglen -= 1
        
        result = ''.join([buf[0][i] for i in range(msglen)])
        LocalFree(buf[0])
        return result

    def FAILED(hr):
        return rffi.cast(HRESULT, hr) < 0

    _GetModuleFileName = winexternal('GetModuleFileNameA',
                                     [HMODULE, rffi.CCHARP, DWORD],
                                     DWORD)

    def GetModuleFileName(module):
        size = 255 # MAX_PATH
        buf = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw')
        res = _GetModuleFileName(module, buf, size)
        if not res:
            return ''
        else:
            return ''.join([buf[i] for i in range(res)])
