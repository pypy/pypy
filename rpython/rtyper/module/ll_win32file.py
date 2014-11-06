"""
The Windows implementation of some posix modules,
based on the Win32 API.
"""
from __future__ import with_statement

from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.tool import rffi_platform as platform
from rpython.tool.sourcetools import func_renamer
from rpython.rlib.objectmodel import specialize


#_______________________________________________________________
# listdir

def make_listdir_impl(traits):
    from rpython.rlib import rwin32
    from rpython.rlib.rwin32file import make_win32_traits

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
    from rpython.rlib import rwin32
    from rpython.rlib.rwin32file import make_win32_traits

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
    from rpython.rlib import rwin32
    from rpython.rlib.rwin32file import make_win32_traits

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
    from rpython.rlib import rwin32
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
