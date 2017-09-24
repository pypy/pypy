"""
Win32 API functions around files.
"""

from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import intmask


def GetCConfigGlobal():
    from rpython.rlib import rwin32

    class CConfigGlobal:
        _compilation_info_ = ExternalCompilationInfo(
            includes = ['windows.h', 'winbase.h', 'sys/stat.h'],
        )
        ERROR_FILE_NOT_FOUND = platform.ConstantInteger(
            'ERROR_FILE_NOT_FOUND')
        ERROR_NO_MORE_FILES = platform.ConstantInteger(
            'ERROR_NO_MORE_FILES')

        GetFileExInfoStandard = platform.ConstantInteger(
            'GetFileExInfoStandard')
        FILE_ATTRIBUTE_DIRECTORY = platform.ConstantInteger(
            'FILE_ATTRIBUTE_DIRECTORY')
        FILE_ATTRIBUTE_READONLY = platform.ConstantInteger(
            'FILE_ATTRIBUTE_READONLY')
        INVALID_FILE_ATTRIBUTES = platform.ConstantInteger(
            'INVALID_FILE_ATTRIBUTES')
        ERROR_SHARING_VIOLATION = platform.ConstantInteger(
            'ERROR_SHARING_VIOLATION')
        ERROR_ACCESS_DENIED = platform.ConstantInteger(
            'ERROR_ACCESS_DENIED')
        MOVEFILE_REPLACE_EXISTING = platform.ConstantInteger(
            'MOVEFILE_REPLACE_EXISTING')
        _S_IFDIR = platform.ConstantInteger('_S_IFDIR')
        _S_IFREG = platform.ConstantInteger('_S_IFREG')
        _S_IFCHR = platform.ConstantInteger('_S_IFCHR')
        _S_IFIFO = platform.ConstantInteger('_S_IFIFO')
        FILE_TYPE_UNKNOWN = platform.ConstantInteger('FILE_TYPE_UNKNOWN')
        FILE_TYPE_CHAR = platform.ConstantInteger('FILE_TYPE_CHAR')
        FILE_TYPE_PIPE = platform.ConstantInteger('FILE_TYPE_PIPE')

        FILE_READ_ATTRIBUTES = platform.ConstantInteger(
            'FILE_READ_ATTRIBUTES')
        FILE_WRITE_ATTRIBUTES = platform.ConstantInteger(
            'FILE_WRITE_ATTRIBUTES')
        OPEN_EXISTING = platform.ConstantInteger(
            'OPEN_EXISTING')
        FILE_ATTRIBUTE_NORMAL = platform.ConstantInteger(
            'FILE_ATTRIBUTE_NORMAL')
        FILE_FLAG_BACKUP_SEMANTICS = platform.ConstantInteger(
            'FILE_FLAG_BACKUP_SEMANTICS')
        VOLUME_NAME_DOS = platform.ConstantInteger('VOLUME_NAME_DOS')
        VOLUME_NAME_NT = platform.ConstantInteger('VOLUME_NAME_NT')

        WIN32_FILE_ATTRIBUTE_DATA = platform.Struct(
            'WIN32_FILE_ATTRIBUTE_DATA',
            [('dwFileAttributes', rwin32.DWORD),
             ('nFileSizeHigh', rwin32.DWORD),
             ('nFileSizeLow', rwin32.DWORD),
             ('ftCreationTime', rwin32.FILETIME),
             ('ftLastAccessTime', rwin32.FILETIME),
             ('ftLastWriteTime', rwin32.FILETIME)])

        BY_HANDLE_FILE_INFORMATION = platform.Struct(
            'BY_HANDLE_FILE_INFORMATION',
            [('dwFileAttributes', rwin32.DWORD),
             ('ftCreationTime', rwin32.FILETIME),
             ('ftLastAccessTime', rwin32.FILETIME),
             ('ftLastWriteTime', rwin32.FILETIME),
             ('dwVolumeSerialNumber', rwin32.DWORD),
             ('nFileSizeHigh', rwin32.DWORD),
             ('nFileSizeLow', rwin32.DWORD),
             ('nNumberOfLinks', rwin32.DWORD),
             ('nFileIndexHigh', rwin32.DWORD),
             ('nFileIndexLow', rwin32.DWORD)])

    return CConfigGlobal

config_global = None


@specialize.memo()
def make_win32_traits(traits):
    from rpython.rlib import rwin32
    global config_global

    if traits.str is unicode:
        suffix = 'W'
    else:
        suffix = 'A'

    class CConfig:
        _compilation_info_ = ExternalCompilationInfo(
            includes = ['windows.h', 'winbase.h', 'sys/stat.h'],
        )
        WIN32_FIND_DATA = platform.Struct(
            'struct _WIN32_FIND_DATA' + suffix,
            # Only interesting fields
            [('dwFileAttributes', rwin32.DWORD),
             ('nFileSizeHigh', rwin32.DWORD),
             ('nFileSizeLow', rwin32.DWORD),
             ('ftCreationTime', rwin32.FILETIME),
             ('ftLastAccessTime', rwin32.FILETIME),
             ('ftLastWriteTime', rwin32.FILETIME),
             ('cFileName', lltype.FixedSizeArray(traits.CHAR, 250))])

    if config_global is None:
        config_global = platform.configure(GetCConfigGlobal())
    config = config_global.copy()
    config.update(platform.configure(CConfig))

    def external(*args, **kwargs):
        kwargs['compilation_info'] = CConfig._compilation_info_
        llfunc = rffi.llexternal(calling_conv='win', *args, **kwargs)
        return staticmethod(llfunc)

    class Win32Traits:
        apisuffix = suffix

        for name in '''WIN32_FIND_DATA WIN32_FILE_ATTRIBUTE_DATA BY_HANDLE_FILE_INFORMATION
                       GetFileExInfoStandard
                       FILE_ATTRIBUTE_DIRECTORY FILE_ATTRIBUTE_READONLY
                       INVALID_FILE_ATTRIBUTES
                       _S_IFDIR _S_IFREG _S_IFCHR _S_IFIFO
                       FILE_TYPE_UNKNOWN FILE_TYPE_CHAR FILE_TYPE_PIPE
                       FILE_READ_ATTRIBUTES FILE_ATTRIBUTE_NORMAL
                       FILE_WRITE_ATTRIBUTES OPEN_EXISTING FILE_FLAG_BACKUP_SEMANTICS
                       VOLUME_NAME_DOS VOLUME_NAME_NT
                       ERROR_FILE_NOT_FOUND ERROR_NO_MORE_FILES
                       ERROR_SHARING_VIOLATION MOVEFILE_REPLACE_EXISTING
                       ERROR_ACCESS_DENIED
                    '''.split():
            locals()[name] = config[name]
        LPWIN32_FIND_DATA    = lltype.Ptr(WIN32_FIND_DATA)
        GET_FILEEX_INFO_LEVELS = rffi.ULONG # an enumeration

        FindFirstFile = external('FindFirstFile' + suffix,
                                 [traits.CCHARP, LPWIN32_FIND_DATA],
                                 rwin32.HANDLE,
                                 save_err=rffi.RFFI_SAVE_LASTERROR)
        FindNextFile = external('FindNextFile' + suffix,
                                [rwin32.HANDLE, LPWIN32_FIND_DATA],
                                rwin32.BOOL,
                                save_err=rffi.RFFI_SAVE_LASTERROR)
        FindClose = external('FindClose',
                             [rwin32.HANDLE],
                             rwin32.BOOL)

        GetFileAttributes = external(
            'GetFileAttributes' + suffix,
            [traits.CCHARP],
            rwin32.DWORD,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        SetFileAttributes = external(
            'SetFileAttributes' + suffix,
            [traits.CCHARP, rwin32.DWORD],
            rwin32.BOOL,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        GetFileAttributesEx = external(
            'GetFileAttributesEx' + suffix,
            [traits.CCHARP, GET_FILEEX_INFO_LEVELS,
             lltype.Ptr(WIN32_FILE_ATTRIBUTE_DATA)],
            rwin32.BOOL,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        GetFileInformationByHandle = external(
            'GetFileInformationByHandle',
            [rwin32.HANDLE, lltype.Ptr(BY_HANDLE_FILE_INFORMATION)],
            rwin32.BOOL,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        GetFileType = external(
            'GetFileType',
            [rwin32.HANDLE],
            rwin32.DWORD,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        LPSTRP = rffi.CArrayPtr(traits.CCHARP)

        GetFullPathName = external(
            'GetFullPathName' + suffix,
            [traits.CCHARP, rwin32.DWORD,
             traits.CCHARP, LPSTRP],
            rwin32.DWORD,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        GetCurrentDirectory = external(
            'GetCurrentDirectory' + suffix,
            [rwin32.DWORD, traits.CCHARP],
            rwin32.DWORD,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        SetCurrentDirectory = external(
            'SetCurrentDirectory' + suffix,
            [traits.CCHARP],
            rwin32.BOOL,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        CreateDirectory = external(
            'CreateDirectory' + suffix,
            [traits.CCHARP, rffi.VOIDP],
            rwin32.BOOL,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        SetEnvironmentVariable = external(
            'SetEnvironmentVariable' + suffix,
            [traits.CCHARP, traits.CCHARP],
            rwin32.BOOL,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        CreateFile = external(
            'CreateFile' + apisuffix,
            [traits.CCHARP, rwin32.DWORD, rwin32.DWORD,
             rwin32.LPSECURITY_ATTRIBUTES, rwin32.DWORD, rwin32.DWORD,
             rwin32.HANDLE],
            rwin32.HANDLE,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        DeleteFile = external(
            'DeleteFile' + suffix,
            [traits.CCHARP],
            rwin32.BOOL,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        MoveFileEx = external(
            'MoveFileEx' + suffix,
            [traits.CCHARP, traits.CCHARP, rwin32.DWORD],
            rwin32.BOOL,
            save_err=rffi.RFFI_SAVE_LASTERROR)

        CreateHardLink = external(
            'CreateHardLink' + suffix,
            [traits.CCHARP, traits.CCHARP, rwin32.LPSECURITY_ATTRIBUTES],
            rwin32.BOOL,
            save_err=rffi.RFFI_SAVE_LASTERROR)

    return Win32Traits

def make_longlong(high, low):
    return (rffi.r_longlong(high) << 32) + rffi.r_longlong(low)

# Seconds between 1.1.1601 and 1.1.1970
secs_between_epochs = 11644473600.0
hns_between_epochs = rffi.r_longlong(116444736000000000)  # units of 100 nsec

def FILE_TIME_to_time_t_float(filetime):
    ft = make_longlong(filetime.c_dwHighDateTime, filetime.c_dwLowDateTime)
    # FILETIME is in units of 100 nsec
    return float(ft) * (1.0 / 10000000.0) - secs_between_epochs

def FILE_TIME_to_time_t_nsec(filetime):
    """Like the previous function, but returns a pair: (integer part
    'time_t' as a r_longlong, fractional part as an int measured in
    nanoseconds).
    """
    ft = make_longlong(filetime.c_dwHighDateTime, filetime.c_dwLowDateTime)
    ft -= hns_between_epochs
    int_part = ft / 10000000
    frac_part = ft - (int_part * 10000000)
    return (int_part, intmask(frac_part) * 100)

def time_t_to_FILE_TIME(time, filetime):
    ft = rffi.r_longlong((time + secs_between_epochs) * 10000000)
    filetime.c_dwHighDateTime = rffi.r_uint(ft >> 32)
    filetime.c_dwLowDateTime = rffi.r_uint(ft)    # masking off high bits

