"""
The Windows implementation of some posix modules,
based on the Win32 API.
"""

from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.tool import rffi_platform as platform
from pypy.tool.sourcetools import func_renamer

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
            return rffi.llexternal(calling_conv='win', *args, **kwargs)

    class Win32Traits:
        apisuffix = suffix

        for name in '''WIN32_FIND_DATA WIN32_FILE_ATTRIBUTE_DATA BY_HANDLE_FILE_INFORMATION
                       GetFileExInfoStandard
                       FILE_ATTRIBUTE_DIRECTORY FILE_ATTRIBUTE_READONLY
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
