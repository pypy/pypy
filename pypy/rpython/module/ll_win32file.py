"""
The Windows implementation of some posix modules,
based on the Win32 API.
"""
from __future__ import with_statement

from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.tool import rffi_platform as platform
from pypy.tool.sourcetools import func_renamer
from pypy.rlib.objectmodel import specialize

def make_win32_traits(traits):
    from pypy.rlib import rwin32

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
        _S_IFDIR = platform.ConstantInteger('_S_IFDIR')
        _S_IFREG = platform.ConstantInteger('_S_IFREG')
        _S_IFCHR = platform.ConstantInteger('_S_IFCHR')
        _S_IFIFO = platform.ConstantInteger('_S_IFIFO')
        FILE_TYPE_UNKNOWN = platform.ConstantInteger('FILE_TYPE_UNKNOWN')
        FILE_TYPE_CHAR = platform.ConstantInteger('FILE_TYPE_CHAR')
        FILE_TYPE_PIPE = platform.ConstantInteger('FILE_TYPE_PIPE')

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
             ('nFileSizeHigh', rwin32.DWORD),
             ('nFileSizeLow', rwin32.DWORD),
             ('nNumberOfLinks', rwin32.DWORD),
             ('nFileIndexHigh', rwin32.DWORD),
             ('nFileIndexLow', rwin32.DWORD),
             ('ftCreationTime', rwin32.FILETIME),
             ('ftLastAccessTime', rwin32.FILETIME),
             ('ftLastWriteTime', rwin32.FILETIME)])

    config = platform.configure(CConfig)

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
                       ERROR_FILE_NOT_FOUND ERROR_NO_MORE_FILES
                       ERROR_SHARING_VIOLATION
                    '''.split():
            locals()[name] = config[name]
        LPWIN32_FIND_DATA    = lltype.Ptr(WIN32_FIND_DATA)
        GET_FILEEX_INFO_LEVELS = rffi.ULONG # an enumeration

        FindFirstFile = external('FindFirstFile' + suffix,
                                 [traits.CCHARP, LPWIN32_FIND_DATA],
                                 rwin32.HANDLE)
        FindNextFile = external('FindNextFile' + suffix,
                                [rwin32.HANDLE, LPWIN32_FIND_DATA],
                                rwin32.BOOL)
        FindClose = external('FindClose',
                             [rwin32.HANDLE],
                             rwin32.BOOL)

        GetFileAttributes = external(
            'GetFileAttributes' + suffix,
            [traits.CCHARP],
            rwin32.DWORD)

        SetFileAttributes = external(
            'SetFileAttributes' + suffix,
            [traits.CCHARP, rwin32.DWORD],
            rwin32.BOOL)

        GetFileAttributesEx = external(
            'GetFileAttributesEx' + suffix,
            [traits.CCHARP, GET_FILEEX_INFO_LEVELS,
             lltype.Ptr(WIN32_FILE_ATTRIBUTE_DATA)],
            rwin32.BOOL)

        GetFileInformationByHandle = external(
            'GetFileInformationByHandle',
            [rwin32.HANDLE, lltype.Ptr(BY_HANDLE_FILE_INFORMATION)],
            rwin32.BOOL)

        GetFileType = external(
            'GetFileType',
            [rwin32.HANDLE],
            rwin32.DWORD)

        LPSTRP = rffi.CArrayPtr(traits.CCHARP)

        GetFullPathName = external(
            'GetFullPathName' + suffix,
            [traits.CCHARP, rwin32.DWORD,
             traits.CCHARP, LPSTRP],
            rwin32.DWORD)

        GetCurrentDirectory = external(
            'GetCurrentDirectory' + suffix,
            [rwin32.DWORD, traits.CCHARP],
            rwin32.DWORD)

        SetCurrentDirectory = external(
            'SetCurrentDirectory' + suffix,
            [traits.CCHARP],
            rwin32.BOOL)

        CreateDirectory = external(
            'CreateDirectory' + suffix,
            [traits.CCHARP, rffi.VOIDP],
            rwin32.BOOL)

        SetEnvironmentVariable = external(
            'SetEnvironmentVariable' + suffix,
            [traits.CCHARP, traits.CCHARP],
            rwin32.BOOL)

        DeleteFile = external(
            'DeleteFile' + suffix,
            [traits.CCHARP],
            rwin32.BOOL)

        MoveFile = external(
            'MoveFile' + suffix,
            [traits.CCHARP, traits.CCHARP],
            rwin32.BOOL)

    return Win32Traits

#_______________________________________________________________
# listdir

def make_listdir_impl(traits):
    from pypy.rlib import rwin32
    win32traits = make_win32_traits(traits)

    if traits.str is unicode:
        def make_listdir_mask(path):
            if path and path[-1] not in (u'/', u'\\', u':'):
                path += u'/'
            return path + u'*.*'

        def skip_listdir(name):
            return name == u"." or name == u".."
    else:
        def make_listdir_mask(path):
            if path and path[-1] not in ('/', '\\', ':'):
                path += '/'
            return path + '*.*'

        def skip_listdir(name):
            return name == "." or name == ".."

    @func_renamer('listdir_llimpl_%s' % traits.str.__name__)
    def listdir_llimpl(path):
        mask = make_listdir_mask(path)
        filedata = lltype.malloc(win32traits.WIN32_FIND_DATA, flavor='raw')
        try:
            result = []
            hFindFile = win32traits.FindFirstFile(mask, filedata)
            if hFindFile == rwin32.INVALID_HANDLE_VALUE:
                error = rwin32.GetLastError()
                if error == win32traits.ERROR_FILE_NOT_FOUND:
                    return result
                else:
                    raise WindowsError(error,  "FindFirstFile failed")
            while True:
                name = traits.charp2str(rffi.cast(traits.CCHARP,
                                                  filedata.c_cFileName))
                if not skip_listdir(name):
                    result.append(name)
                if not win32traits.FindNextFile(hFindFile, filedata):
                    break
            # FindNextFile sets error to ERROR_NO_MORE_FILES if
            # it got to the end of the directory
            error = rwin32.GetLastError()
            win32traits.FindClose(hFindFile)
            if error == win32traits.ERROR_NO_MORE_FILES:
                return result
            else:
                raise WindowsError(error,  "FindNextFile failed")
        finally:
            lltype.free(filedata, flavor='raw')

    return listdir_llimpl

#_______________________________________________________________
# chdir

def make_chdir_impl(traits):
    from pypy.rlib import rwin32
    win32traits = make_win32_traits(traits)

    if traits.str is unicode:
        def isUNC(path):
            return path[0] == u'\\' or path[0] == u'/'
        def magic_envvar(path):
            return u'=' + path[0] + u':'
    else:
        def isUNC(path):
            return path[0] == '\\' or path[0] == '/'
        def magic_envvar(path):
            return '=' + path[0] + ':'

    @func_renamer('chdir_llimpl_%s' % traits.str.__name__)
    def chdir_llimpl(path):
        """This is a reimplementation of the C library's chdir function,
        but one that produces Win32 errors instead of DOS error codes.
        chdir is essentially a wrapper around SetCurrentDirectory; however,
        it also needs to set "magic" environment variables indicating
        the per-drive current directory, which are of the form =<drive>:
        """
        if not win32traits.SetCurrentDirectory(path):
            raise rwin32.lastWindowsError()
        MAX_PATH = rwin32.MAX_PATH
        assert MAX_PATH > 0

        with traits.scoped_alloc_buffer(MAX_PATH) as path:
            res = win32traits.GetCurrentDirectory(MAX_PATH + 1, path.raw)
            if not res:
                raise rwin32.lastWindowsError()
            res = rffi.cast(lltype.Signed, res)
            assert res > 0
            if res <= MAX_PATH + 1:
                new_path = path.str(res)
            else:
                with traits.scoped_alloc_buffer(res) as path:
                    res = win32traits.GetCurrentDirectory(res, path.raw)
                    if not res:
                        raise rwin32.lastWindowsError()
                    res = rffi.cast(lltype.Signed, res)
                    assert res > 0
                    new_path = path.str(res)
        if isUNC(new_path):
            return
        if not win32traits.SetEnvironmentVariable(magic_envvar(new_path), new_path):
            raise rwin32.lastWindowsError()

    return chdir_llimpl

#_______________________________________________________________
# chmod

def make_chmod_impl(traits):
    from pypy.rlib import rwin32
    win32traits = make_win32_traits(traits)

    @func_renamer('chmod_llimpl_%s' % traits.str.__name__)
    def chmod_llimpl(path, mode):
        attr = win32traits.GetFileAttributes(path)
        if attr == win32traits.INVALID_FILE_ATTRIBUTES:
            raise rwin32.lastWindowsError()
        if mode & 0200: # _S_IWRITE
            attr &= ~win32traits.FILE_ATTRIBUTE_READONLY
        else:
            attr |= win32traits.FILE_ATTRIBUTE_READONLY
        if not win32traits.SetFileAttributes(path, attr):
            raise rwin32.lastWindowsError()

    return chmod_llimpl

#_______________________________________________________________
# getfullpathname

def make_getfullpathname_impl(traits):
    from pypy.rlib import rwin32
    win32traits = make_win32_traits(traits)

    @func_renamer('getfullpathname_llimpl_%s' % traits.str.__name__)
    def getfullpathname_llimpl(path):
        nBufferLength = rwin32.MAX_PATH + 1
        lpBuffer = lltype.malloc(traits.CCHARP.TO, nBufferLength, flavor='raw')
        try:
            res = win32traits.GetFullPathName(
                path, rffi.cast(rwin32.DWORD, nBufferLength),
                lpBuffer, lltype.nullptr(win32traits.LPSTRP.TO))
            if res == 0:
                raise rwin32.lastWindowsError("_getfullpathname failed")
            result = traits.charp2str(lpBuffer)
            return result
        finally:
            lltype.free(lpBuffer, flavor='raw')

    return getfullpathname_llimpl

def make_utime_impl(traits):
    from pypy.rlib import rwin32
    win32traits = make_win32_traits(traits)
    from pypy.rpython.module.ll_os_stat import time_t_to_FILE_TIME

    class CConfig:
        _compilation_info_ = ExternalCompilationInfo(
            includes = ['windows.h'],
            )

        FILE_WRITE_ATTRIBUTES = platform.ConstantInteger(
            'FILE_WRITE_ATTRIBUTES')
        OPEN_EXISTING = platform.ConstantInteger(
            'OPEN_EXISTING')
        FILE_FLAG_BACKUP_SEMANTICS = platform.ConstantInteger(
            'FILE_FLAG_BACKUP_SEMANTICS')
    globals().update(platform.configure(CConfig))

    CreateFile = rffi.llexternal(
        'CreateFile' + win32traits.apisuffix,
        [traits.CCHARP, rwin32.DWORD, rwin32.DWORD,
         rwin32.LPSECURITY_ATTRIBUTES, rwin32.DWORD, rwin32.DWORD,
         rwin32.HANDLE],
        rwin32.HANDLE,
        calling_conv='win')

    GetSystemTime = rffi.llexternal(
        'GetSystemTime',
        [lltype.Ptr(rwin32.SYSTEMTIME)],
        lltype.Void,
        calling_conv='win')

    SystemTimeToFileTime = rffi.llexternal(
        'SystemTimeToFileTime',
        [lltype.Ptr(rwin32.SYSTEMTIME),
         lltype.Ptr(rwin32.FILETIME)],
        rwin32.BOOL,
        calling_conv='win')

    SetFileTime = rffi.llexternal(
        'SetFileTime',
        [rwin32.HANDLE,
         lltype.Ptr(rwin32.FILETIME),
         lltype.Ptr(rwin32.FILETIME),
         lltype.Ptr(rwin32.FILETIME)],
        rwin32.BOOL,
        calling_conv = 'win')

    @specialize.argtype(1)
    def os_utime_llimpl(path, tp):
        hFile = CreateFile(path,
                           FILE_WRITE_ATTRIBUTES, 0,
                           None, OPEN_EXISTING,
                           FILE_FLAG_BACKUP_SEMANTICS,
                           rwin32.NULL_HANDLE)
        if hFile == rwin32.INVALID_HANDLE_VALUE:
            raise rwin32.lastWindowsError()
        ctime = lltype.nullptr(rwin32.FILETIME)
        atime = lltype.malloc(rwin32.FILETIME, flavor='raw')
        mtime = lltype.malloc(rwin32.FILETIME, flavor='raw')
        try:
            if tp is None:
                now = lltype.malloc(rwin32.SYSTEMTIME, flavor='raw')
                try:
                    GetSystemTime(now)
                    if (not SystemTimeToFileTime(now, atime) or
                        not SystemTimeToFileTime(now, mtime)):
                        raise rwin32.lastWindowsError()
                finally:
                    lltype.free(now, flavor='raw')
            else:
                actime, modtime = tp
                time_t_to_FILE_TIME(actime, atime)
                time_t_to_FILE_TIME(modtime, mtime)
            if not SetFileTime(hFile, ctime, atime, mtime):
                raise rwin32.lastWindowsError()
        finally:
            rwin32.CloseHandle(hFile)
            lltype.free(atime, flavor='raw')
            lltype.free(mtime, flavor='raw')

    return os_utime_llimpl
