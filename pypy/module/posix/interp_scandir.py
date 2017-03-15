import stat
from errno import ENOENT
from rpython.rlib import rgc
from rpython.rlib import rposix, rposix_scandir, rposix_stat

from pypy.interpreter.gateway import unwrap_spec, WrappedDefault, interp2app
from pypy.interpreter.error import OperationError, oefmt, wrap_oserror2
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.baseobjspace import W_Root

from pypy.module.posix.interp_posix import unwrap_fd, build_stat_result, _WIN32


def scandir(space, w_path=None):
    "scandir(path='.') -> iterator of DirEntry objects for given path"
    if _WIN32:
        raise NotImplementedError("XXX WIN32")

    if space.is_none(w_path):
        w_path = space.newunicode(u".")
    if space.isinstance_w(w_path, space.w_bytes):
        path_bytes = space.bytes0_w(w_path)
        result_is_bytes = True
    else:
        path_bytes = space.fsencode_w(w_path)
        result_is_bytes = False

    try:
        dirp = rposix_scandir.opendir(path_bytes)
    except OSError as e:
        raise wrap_oserror2(space, e, w_path, eintr_retry=False)
    path_prefix = path_bytes
    if len(path_prefix) > 0 and path_prefix[-1] != '/':
        path_prefix += '/'
    w_path_prefix = space.newbytes(path_prefix)
    if not result_is_bytes:
        w_path_prefix = space.fsdecode(w_path_prefix)
    if rposix.HAVE_FSTATAT:
        dirfd = rposix.c_dirfd(dirp)
    else:
        dirfd = -1
    return W_ScandirIterator(space, dirp, dirfd, w_path_prefix, result_is_bytes)


class W_ScandirIterator(W_Root):
    _in_next = False

    def __init__(self, space, dirp, dirfd, w_path_prefix, result_is_bytes):
        self.space = space
        self.dirp = dirp
        self.dirfd = dirfd
        self.w_path_prefix = w_path_prefix
        self.result_is_bytes = result_is_bytes

    @rgc.must_be_light_finalizer
    def __del__(self):
        if self.dirp:
            rposix_scandir.closedir(self.dirp)

    def iter_w(self):
        return self

    def fail(self, err=None):
        dirp = self.dirp
        if dirp:
            self.dirfd = -1
            self.dirp = rposix_scandir.NULL_DIRP
            rposix_scandir.closedir(dirp)
        if err is None:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        else:
            raise err

    def next_w(self):
        if not self.dirp:
            raise self.fail()
        if self._in_next:
            raise self.fail(oefmt(self.space.w_RuntimeError,
               "cannot use ScandirIterator from multiple threads concurrently"))
        self._in_next = True
        try:
            #
            space = self.space
            while True:
                try:
                    entry = rposix_scandir.nextentry(self.dirp)
                except OSError as e:
                    raise self.fail(wrap_oserror2(space, e, self.w_path_prefix,
                                                  eintr_retry=False))
                if not entry:
                    raise self.fail()
                assert rposix_scandir.has_name_bytes(entry)
                name = rposix_scandir.get_name_bytes(entry)
                if name != '.' and name != '..':
                    break
            #
            known_type = rposix_scandir.get_known_type(entry)
            inode = rposix_scandir.get_inode(entry)
        finally:
            self._in_next = False
        direntry = W_DirEntry(self, name, known_type, inode)
        return direntry


W_ScandirIterator.typedef = TypeDef(
    'posix.ScandirIterator',
    __iter__ = interp2app(W_ScandirIterator.iter_w),
    __next__ = interp2app(W_ScandirIterator.next_w),
)
W_ScandirIterator.typedef.acceptable_as_base_class = False


class FileNotFound(Exception):
    pass

assert 0 <= rposix_scandir.DT_UNKNOWN <= 255
assert 0 <= rposix_scandir.DT_REG <= 255
assert 0 <= rposix_scandir.DT_DIR <= 255
assert 0 <= rposix_scandir.DT_LNK <= 255
FLAG_STAT  = 256
FLAG_LSTAT = 512


class W_DirEntry(W_Root):
    w_path = None

    def __init__(self, scandir_iterator, name, known_type, inode):
        self.space = scandir_iterator.space
        self.scandir_iterator = scandir_iterator
        self.name = name     # always bytes on Posix
        self.inode = inode
        self.flags = known_type
        assert known_type == (known_type & 255)
        #
        w_name = self.space.newbytes(name)
        if not scandir_iterator.result_is_bytes:
            w_name = self.space.fsdecode(w_name)
        self.w_name = w_name

    def descr_repr(self, space):
        u = space.unicode_w(space.repr(self.w_name))
        return space.newunicode(u"<DirEntry %s>" % u)

    def fget_name(self, space):
        return self.w_name

    def fget_path(self, space):
        w_path = self.w_path
        if w_path is None:
            w_path_prefix = self.scandir_iterator.w_path_prefix
            w_path = space.add(w_path_prefix, self.w_name)
            self.w_path = w_path
        return w_path

    # The internal methods, used to implement the public methods at
    # the end of the class.  Every method only calls methods *before*
    # it in program order, so there is no cycle.

    def get_lstat(self):
        """Get the lstat() of the direntry."""
        if (self.flags & FLAG_LSTAT) == 0:
            # Unlike CPython, try to use fstatat() if possible
            dirfd = self.scandir_iterator.dirfd
            if dirfd != -1 and rposix.HAVE_FSTATAT:
                st = rposix_stat.fstatat(self.name, dirfd,
                                         follow_symlinks=False)
            else:
                path = self.space.fsencode_w(self.fget_path(self.space))
                st = rposix_stat.lstat(path)
            self.d_lstat = st
            self.flags |= FLAG_LSTAT
        return self.d_lstat

    def get_stat(self):
        """Get the stat() of the direntry.  This is implemented in
        such a way that it won't do both a stat() and a lstat().
        """
        if (self.flags & FLAG_STAT) == 0:
            # We don't have the 'd_stat'.  If the known_type says the
            # direntry is not a DT_LNK, then try to get and cache the
            # 'd_lstat' instead.  Then, or if we already have a
            # 'd_lstat' from before, *and* if the 'd_lstat' is not a
            # S_ISLNK, we can reuse it unchanged for 'd_stat'.
            #
            # Note how, in the common case where the known_type says
            # it is a DT_REG or DT_DIR, then we call and cache lstat()
            # and that's it.  Also note that in a d_type-less OS or on
            # a filesystem that always answer DT_UNKNOWN, this method
            # will instead only call at most stat(), but not cache it
            # as 'd_lstat'.
            known_type = self.flags & 255
            if (known_type != rposix_scandir.DT_UNKNOWN and
                known_type != rposix_scandir.DT_LNK):
                self.get_lstat()    # fill the 'd_lstat' cache
                have_lstat = True
            else:
                have_lstat = (self.flags & FLAG_LSTAT) != 0

            if have_lstat:
                # We have the lstat() but not the stat().  They are
                # the same, unless the 'd_lstat' is a S_IFLNK.
                must_call_stat = stat.S_ISLNK(self.d_lstat.st_mode)
            else:
                must_call_stat = True

            if must_call_stat:
                # Must call stat().  Try to use fstatat() if possible
                dirfd = self.scandir_iterator.dirfd
                if dirfd != -1 and rposix.HAVE_FSTATAT:
                    st = rposix_stat.fstatat(self.name, dirfd,
                                             follow_symlinks=True)
                else:
                    path = self.space.fsencode_w(self.fget_path(self.space))
                    st = rposix_stat.stat(path)
            else:
                st = self.d_lstat

            self.d_stat = st
            self.flags |= FLAG_STAT
        return self.d_stat

    def get_stat_or_lstat(self, follow_symlinks):
        if follow_symlinks:
            return self.get_stat()
        else:
            return self.get_lstat()

    def check_mode(self, follow_symlinks):
        """Get the stat() or lstat() of the direntry, and return the
        S_IFMT.  If calling stat()/lstat() gives us ENOENT, return -1
        instead; it is better to give up and answer "no, not this type"
        to requests, rather than propagate the error.
        """
        try:
            st = self.get_stat_or_lstat(follow_symlinks)
        except OSError as e:
            if e.errno == ENOENT:    # not found
                return -1
            raise wrap_oserror2(self.space, e, self.fget_path(self.space),
                                eintr_retry=False)
        return stat.S_IFMT(st.st_mode)

    def is_dir(self, follow_symlinks):
        known_type = self.flags & 255
        if known_type != rposix_scandir.DT_UNKNOWN:
            if known_type == rposix_scandir.DT_DIR:
                return True
            elif follow_symlinks and known_type == rposix_scandir.DT_LNK:
                pass    # don't know in this case
            else:
                return False
        return self.check_mode(follow_symlinks) == stat.S_IFDIR

    def is_file(self, follow_symlinks):
        known_type = self.flags & 255
        if known_type != rposix_scandir.DT_UNKNOWN:
            if known_type == rposix_scandir.DT_REG:
                return True
            elif follow_symlinks and known_type == rposix_scandir.DT_LNK:
                pass    # don't know in this case
            else:
                return False
        return self.check_mode(follow_symlinks) == stat.S_IFREG

    def is_symlink(self):
        """Check if the direntry is a symlink.  May get the lstat()."""
        known_type = self.flags & 255
        if known_type != rposix_scandir.DT_UNKNOWN:
            return known_type == rposix_scandir.DT_LNK
        return self.check_mode(follow_symlinks=False) == stat.S_IFLNK

    @unwrap_spec(follow_symlinks=bool)
    def descr_is_dir(self, space, __kwonly__, follow_symlinks=True):
        """return True if the entry is a directory; cached per entry"""
        return space.newbool(self.is_dir(follow_symlinks))

    @unwrap_spec(follow_symlinks=bool)
    def descr_is_file(self, space, __kwonly__, follow_symlinks=True):
        """return True if the entry is a file; cached per entry"""
        return space.newbool(self.is_file(follow_symlinks))

    def descr_is_symlink(self, space):
        """return True if the entry is a symbolic link; cached per entry"""
        return space.newbool(self.is_symlink())

    @unwrap_spec(follow_symlinks=bool)
    def descr_stat(self, space, __kwonly__, follow_symlinks=True):
        """return stat_result object for the entry; cached per entry"""
        try:
            st = self.get_stat_or_lstat(follow_symlinks)
        except OSError as e:
            raise wrap_oserror2(space, e, self.fget_path(space),
                                eintr_retry=False)
        return build_stat_result(space, st)

    def descr_inode(self, space):
        return space.newint(self.inode)


W_DirEntry.typedef = TypeDef(
    'posix.DirEntry',
    __repr__ = interp2app(W_DirEntry.descr_repr),
    name = GetSetProperty(W_DirEntry.fget_name,
                          doc="the entry's base filename, relative to "
                              'scandir() "path" argument'),
    path = GetSetProperty(W_DirEntry.fget_path,
                          doc="the entry's full path name; equivalent to "
                              "os.path.join(scandir_path, entry.name)"),
    is_dir = interp2app(W_DirEntry.descr_is_dir),
    is_file = interp2app(W_DirEntry.descr_is_file),
    is_symlink = interp2app(W_DirEntry.descr_is_symlink),
    stat = interp2app(W_DirEntry.descr_stat),
    inode = interp2app(W_DirEntry.descr_inode),
)
W_DirEntry.typedef.acceptable_as_base_class = False
