from rpython.rlib import rposix, rwin32
from rpython.rlib.objectmodel import specialize
from rpython.rtyper.lltypesystem import lltype, rffi


if not rwin32.WIN32:
    @specialize.argtype(0)
    def opendir(path):
        path = rposix._as_bytes0(path)
        return opendir_bytes(path)

    def opendir_bytes(path):
        dirp = rposix.c_opendir(path)
        if not dirp:
            raise OSError(rposix.get_saved_errno(), "opendir failed")
        return dirp

    def closedir(dirp):
        rposix.c_closedir(dirp)

    NULL_DIRP = lltype.nullptr(rposix.DIRP.TO)

    def nextentry(dirp):
        """Read the next entry and returns an opaque object.
        Use the methods has_xxx() and get_xxx() to read from that
        opaque object.  The opaque object is valid until the next
        time nextentry() or closedir() is called.  This may raise
        OSError, or return a NULL pointer when exhausted.  Note
        that this doesn't filter out the "." and ".." entries.
        """
        direntp = rposix.c_readdir(dirp)
        if direntp:
            error = rposix.get_saved_errno()
            if error:
                raise OSError(error, "readdir failed")
        return direntp

    def get_name_bytes(direntp):
        namep = rffi.cast(rffi.CCHARP, direntp.c_d_name)
        return rffi.charp2str(namep)

    DT_UNKNOWN = rposix.dirent_config.get('DT_UNKNOWN', 0)
    DT_REG = rposix.dirent_config.get('DT_REG', 255)
    DT_DIR = rposix.dirent_config.get('DT_DIR', 255)
    DT_LNK = rposix.dirent_config.get('DT_LNK', 255)

    def get_known_type(direntp):
        if rposix.HAVE_D_TYPE:
            return rffi.getintfield(direntp, 'c_d_type')
        return DT_UNKNOWN

    def get_inode(direntp):
        return rffi.getintfield(direntp, 'c_d_ino')

else:
    # ----- Win32 version -----
    from rpython.rlib._os_support import unicode_traits
    from rpython.rlib.rwin32file import make_win32_traits

    win32traits = make_win32_traits(unicode_traits)


    class DirP:
        def __init__(self):
            self.filedata = lltype.malloc(win32traits.WIN32_FIND_DATA, flavor='raw')
            self.hFindFile = rwin32.INVALID_HANDLE_VALUE

        def close(self):
            lltype.free(self.filedata, flavor='raw')
            if self.hFindFile != rwin32.INVALID_HANDLE_VALUE:
                win32traits.FindClose(self.hFindFile)

    class DirEntP:
        def __init__(self, filedata):
            self.filedata = filedata
            # ^^^ note that this structure is overwritten by the next() call, so
            # we must copy a few pieces of information out of it now:
            self.dwFileAttributes = filedata.c_dwFileAttributes
            self.CreationTimeLow = filedata.c_ftCreationTime.c_dwLowDateTime
            self.CreationTimeHigh = filedata.c_ftCreationTime.c_dwHighDateTime
            self.LastAccessTimeLow = filedata.c_ftLastAccessTime.c_dwLowDateTime
            self.LastAccessTimeHigh = filedata.c_ftLastAccessTime.c_dwHighDateTime
            self.LastWriteTimeLow = filedata.c_ftLastWriteTime.c_dwLowDateTime
            self.LastWriteTimeHigh = filedata.c_ftLastWriteTime.c_dwHighDateTime
            self.nFileSizeHigh = filedata.c_nFileSizeHigh
            self.nFileSizeLow = filedata.c_nFileSizeLow


    # must only be called with unicode!
    def opendir(path):
        if len(path) == 0:
            path = u'.'
        if path[-1] not in (u'\\', u'/', u':'):
            path += u'\\'
        mask = path + u'*.*'
        dirp = DirP()
        hFindFile = win32traits.FindFirstFile(mask, dirp.filedata)
        if hFindFile == rwin32.INVALID_HANDLE_VALUE:
            error = rwin32.GetLastError_saved()
            dirp.close()
            raise WindowsError(error,  "FindFirstFileW failed")
        dirp.hFindFile = hFindFile
        dirp.first_time = True
        return dirp

    def closedir(dirp):
        dirp.close()

    NULL_DIRP = None

    def nextentry(dirp):
        """Read the next entry and returns an opaque object.
        Use the methods has_xxx() and get_xxx() to read from that
        opaque object.  The opaque object is valid until the next
        time nextentry() or closedir() is called.  This may raise
        WindowsError, or return None when exhausted.  Note
        that this doesn't filter out the "." and ".." entries.
        """
        if dirp.first_time:
            dirp.first_time = False
        else:
            if not win32traits.FindNextFile(dirp.hFindFile, dirp.filedata):
                # error or no more files
                error = rwin32.GetLastError_saved()
                if error == win32traits.ERROR_NO_MORE_FILES:
                    return None
                raise WindowsError(error,  "FindNextFileW failed")
        return DirEntP(dirp.filedata)

    def get_name_unicode(direntp):
        return unicode_traits.charp2str(rffi.cast(unicode_traits.CCHARP,
                                                  direntp.filedata.c_cFileName))

    def get_known_type(filedata):
        return 0

    def get_inode(filedata):
        return None
