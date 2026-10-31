from rpython.rlib import rwin32
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rwin32file import make_win32_traits
from rpython.rlib._os_support import utf8_traits
from rpython.translator import cdir
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.rposix import get_saved_errno
from rpython.rlib.rutf8 import codepoints_in_utf8


# XXX: pypy_GetFinalPathNameByHandle is needed to call the dynamically
# found GetFinalPathNameByHandle function with a non-standard calling
# convention. currently FuncType pointer calls w/ non-standard calling
# conventions don't work after translation
separate_module_source = """\
DWORD
pypy_GetFinalPathNameByHandle(FARPROC address, HANDLE hFile,
                              LPTSTR lpszFilePath, DWORD cchFilePath,
                              DWORD dwFlags) {
    DWORD (WINAPI *func)(HANDLE, LPTSTR, DWORD, DWORD);
    *(FARPROC*)&func = address;
    return func(hFile, lpszFilePath, cchFilePath, dwFlags);
}

DWORD
pypy_Getppid()
    /* Copied from CPython win32_getppid */
{
    HANDLE snapshot;
    DWORD mypid;
    DWORD result = (DWORD)(-1);
    BOOL have_record;
    PROCESSENTRY32 pe;

    mypid = getpid(); /* This function never fails */

    snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snapshot == INVALID_HANDLE_VALUE)
        return (DWORD)(-1);
    pe.dwSize = sizeof(pe);
    have_record = Process32First(snapshot, &pe);
    while (have_record) {
        if (mypid == pe.th32ProcessID) {
            result = pe.th32ParentProcessID;
            break;
        }
        have_record = Process32Next(snapshot, &pe);
    }
    CloseHandle(snapshot);
    return result;
}    
"""
eci = ExternalCompilationInfo(
    includes=['windows.h', 'tlhelp32.h'],
    include_dirs=[cdir],
    post_include_bits=[
        "RPY_EXTERN DWORD "
        "pypy_GetFinalPathNameByHandle(FARPROC, HANDLE, LPTSTR, DWORD, DWORD);",
        "RPY_EXTERN DWORD ",
        "pypy_Getppid();",
    ],
    separate_module_sources=[separate_module_source])
pypy_GetFinalPathNameByHandle = rffi.llexternal(
    'pypy_GetFinalPathNameByHandle',
    [rffi.VOIDP, rwin32.HANDLE, rffi.CWCHARP, rwin32.DWORD, rwin32.DWORD],
    rwin32.DWORD, compilation_info=eci)
pypy_Getppid = rffi.llexternal(
    'pypy_Getppid', [], rwin32.DWORD, compilation_info=eci)


# plain NotImplementedError is invalid RPython
class LLNotImplemented(Exception):

    def __init__(self, msg):
        self.msg = msg


def make_traits(traits):
    win32traits = make_win32_traits(traits)

    class NTTraits(win32traits):

        GetFinalPathNameByHandle_HANDLE = lltype.nullptr(rffi.VOIDP.TO)

        def check_GetFinalPathNameByHandle(self):
            if (self.GetFinalPathNameByHandle_HANDLE !=
                lltype.nullptr(rffi.VOIDP.TO)):
                return True

            from rpython.rlib.rdynload import GetModuleHandle, dlsym
            hKernel32 = GetModuleHandle("KERNEL32")
            try:
                func = dlsym(hKernel32, 'GetFinalPathNameByHandleW')
            except KeyError:
                return False

            self.GetFinalPathNameByHandle_HANDLE = func
            return True

        def GetFinalPathNameByHandle(self, *args):
            assert (self.GetFinalPathNameByHandle_HANDLE !=
                    lltype.nullptr(rffi.VOIDP.TO))
            return pypy_GetFinalPathNameByHandle(
                self.GetFinalPathNameByHandle_HANDLE, *args)

    return NTTraits()


def make__getfileinformation_impl(traits):
    win32traits = make_traits(traits)

    def _getfileinformation_llimpl(fd):
        hFile = rwin32.get_osfhandle(fd)
        with lltype.scoped_alloc(
            win32traits.BY_HANDLE_FILE_INFORMATION) as info:
            if win32traits.GetFileInformationByHandle(hFile, info) == 0:
                raise rwin32.lastSavedWindowsError("_getfileinformation")
            return (rffi.cast(lltype.Signed, info.c_dwVolumeSerialNumber),
                    rffi.cast(lltype.Signed, info.c_nFileIndexHigh),
                    rffi.cast(lltype.Signed, info.c_nFileIndexLow))

    return _getfileinformation_llimpl


def make__getfinalpathname_impl(traits):
    win32traits = make_traits(traits)

    def _getfinalpathname_llimpl(utf8):
        if not win32traits.check_GetFinalPathNameByHandle():
            raise LLNotImplemented("GetFinalPathNameByHandle not available on "
                                   "this platform")
        with rffi.scoped_utf82wcharp(utf8, codepoints_in_utf8(utf8)) as buf:
            hFile = win32traits.CreateFile(buf, 0, 0, None,
                                       win32traits.OPEN_EXISTING,
                                       win32traits.FILE_FLAG_BACKUP_SEMANTICS,
                                       rwin32.NULL_HANDLE)
        if hFile == rwin32.INVALID_HANDLE_VALUE:
            raise rwin32.lastSavedWindowsError("CreateFile")

        VOLUME_NAME_DOS = rffi.cast(rwin32.DWORD, win32traits.VOLUME_NAME_DOS)
        try:
            usize = win32traits.GetFinalPathNameByHandle(
                hFile,
                lltype.nullptr(traits.CCHARP.TO),
                rffi.cast(rwin32.DWORD, 0),
                VOLUME_NAME_DOS)
            if usize == 0:
                raise rwin32.lastSavedWindowsError("GetFinalPathNameByHandle")

            size = rffi.cast(lltype.Signed, usize)
            with rffi.scoped_alloc_unicodebuffer(size + 1) as buf:
                result = win32traits.GetFinalPathNameByHandle(
                    hFile,
                    buf.raw,
                    usize,
                    VOLUME_NAME_DOS)
                if result == 0:
                    raise rwin32.lastSavedWindowsError("GetFinalPathNameByHandle")
                res = buf.str(rffi.cast(lltype.Signed, result))
                return res.encode('utf8'), len(res)
        finally:
            rwin32.CloseHandle(hFile)

    return _getfinalpathname_llimpl


_getfileinformation = make__getfileinformation_impl(utf8_traits)
_getfinalpathname = make__getfinalpathname_impl(utf8_traits)


_PULARGE = rffi.CArrayPtr(rffi.ULONGLONG)
_GetDiskFreeSpaceExW = rffi.llexternal(
    'GetDiskFreeSpaceExW',
    [rffi.CWCHARP, _PULARGE, _PULARGE, _PULARGE],
    rwin32.BOOL,
    compilation_info=eci,
    save_err=rffi.RFFI_SAVE_LASTERROR)

ERROR_DIRECTORY = 267

def win32_getdiskusage(utf8):
    ncp = codepoints_in_utf8(utf8)
    with rffi.scoped_utf82wcharp(utf8, ncp) as buf:
        with lltype.scoped_alloc(rffi.CArray(rffi.ULONGLONG), 1) as avail_p:
            with lltype.scoped_alloc(rffi.CArray(rffi.ULONGLONG), 1) as total_p:
                with lltype.scoped_alloc(rffi.CArray(rffi.ULONGLONG), 1) as free_p:
                    ret = _GetDiskFreeSpaceExW(buf, avail_p, total_p, free_p)
                    if ret:
                        total = rffi.cast(lltype.SignedLongLong, total_p[0])
                        free_ = rffi.cast(lltype.SignedLongLong, free_p[0])
                        return total, free_
                    if rwin32.GetLastError_saved() != ERROR_DIRECTORY:
                        raise rwin32.lastSavedWindowsError("GetDiskFreeSpaceExW")
    # ERROR_DIRECTORY: path is a file; retry with its parent directory
    idx = utf8.rfind('\\')
    if idx < 0:
        idx = utf8.rfind('/')
    dir_utf8 = utf8[:idx] if idx >= 0 else utf8
    ncp2 = codepoints_in_utf8(dir_utf8)
    with rffi.scoped_utf82wcharp(dir_utf8, ncp2) as buf2:
        with lltype.scoped_alloc(rffi.CArray(rffi.ULONGLONG), 1) as avail_p:
            with lltype.scoped_alloc(rffi.CArray(rffi.ULONGLONG), 1) as total_p:
                with lltype.scoped_alloc(rffi.CArray(rffi.ULONGLONG), 1) as free_p:
                    ret = _GetDiskFreeSpaceExW(buf2, avail_p, total_p, free_p)
                    if not ret:
                        raise rwin32.lastSavedWindowsError("GetDiskFreeSpaceExW")
                    total = rffi.cast(lltype.SignedLongLong, total_p[0])
                    free_ = rffi.cast(lltype.SignedLongLong, free_p[0])
    return total, free_


ERROR_MORE_DATA = 234
ERROR_NO_MORE_FILES = 18

_GetLogicalDriveStringsW = rffi.llexternal(
    'GetLogicalDriveStringsW',
    [rwin32.DWORD, rffi.CWCHARP],
    rwin32.DWORD,
    compilation_info=eci,
    save_err=rffi.RFFI_SAVE_LASTERROR)

_FindFirstVolumeW = rffi.llexternal(
    'FindFirstVolumeW',
    [rffi.CWCHARP, rwin32.DWORD],
    rwin32.HANDLE,
    compilation_info=eci,
    save_err=rffi.RFFI_SAVE_LASTERROR)

_FindNextVolumeW = rffi.llexternal(
    'FindNextVolumeW',
    [rwin32.HANDLE, rffi.CWCHARP, rwin32.DWORD],
    rwin32.BOOL,
    compilation_info=eci,
    save_err=rffi.RFFI_SAVE_LASTERROR)

_FindVolumeClose = rffi.llexternal(
    'FindVolumeClose',
    [rwin32.HANDLE],
    rwin32.BOOL,
    compilation_info=eci)

_GetVolumePathNameW = rffi.llexternal(
    'GetVolumePathNameW',
    [rffi.CWCHARP, rffi.CWCHARP, rwin32.DWORD],
    rwin32.BOOL,
    compilation_info=eci,
    save_err=rffi.RFFI_SAVE_LASTERROR)


def win32_listdrives():
    """The drives in the system, as a list of utf8 strings."""
    # the number of drives is bounded, so 256 wchars is always enough
    size = 256
    with lltype.scoped_alloc(rffi.CWCHARP.TO, size) as buf:
        buflen = rffi.cast(lltype.Signed, _GetLogicalDriveStringsW(
            rffi.cast(rwin32.DWORD, size), buf))
        if buflen == 0:
            raise rwin32.lastSavedWindowsError("GetLogicalDriveStringsW")
        if buflen >= size:
            raise WindowsError(ERROR_MORE_DATA, "GetLogicalDriveStringsW")
        # NUL-separated strings, plus a final NUL that buflen counts
        return rffi.wcharpsize2utf8(buf, buflen - 1).split('\x00')


def win32_listvolumes():
    """The volumes in the system, as a list of utf8 GUID paths."""
    result = []
    size = rwin32.MAX_PATH + 1
    with lltype.scoped_alloc(rffi.CWCHARP.TO, size) as buf:
        hFind = _FindFirstVolumeW(buf, rffi.cast(rwin32.DWORD, size))
        if hFind == rwin32.INVALID_HANDLE_VALUE:
            if rwin32.GetLastError_saved() != ERROR_NO_MORE_FILES:
                raise rwin32.lastSavedWindowsError("FindFirstVolumeW")
            return result
        try:
            while True:
                utf8, lgt = rffi.wcharp2utf8(buf)
                result.append(utf8)
                if not _FindNextVolumeW(hFind, buf,
                                        rffi.cast(rwin32.DWORD, size)):
                    if rwin32.GetLastError_saved() != ERROR_NO_MORE_FILES:
                        raise rwin32.lastSavedWindowsError("FindNextVolumeW")
                    break
        finally:
            _FindVolumeClose(hFind)
    return result


def win32_getvolumepathname(utf8):
    """The mount point of the volume holding 'utf8', as utf8."""
    ncp = codepoints_in_utf8(utf8)
    # the volume path is no longer than the whole path
    size = len(utf8) + 1
    if size < rwin32.MAX_PATH:
        size = rwin32.MAX_PATH
    with rffi.scoped_utf82wcharp(utf8, ncp) as path:
        with lltype.scoped_alloc(rffi.CWCHARP.TO, size) as buf:
            if not _GetVolumePathNameW(path, buf,
                                       rffi.cast(rwin32.DWORD, size)):
                raise rwin32.lastSavedWindowsError("_getvolumepathname")
            return rffi.wcharp2utf8(buf)


def win32_getppid():
    ret = pypy_Getppid()
    if ret == rffi.cast(rwin32.DWORD, -1):
        raise OSError(get_saved_errno(), 'getppid failed')
    return ret
