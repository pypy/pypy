import os
import stat, errno

UID = 1000
GID = 1000
ATIME = MTIME = CTIME = 0
INO_COUNTER = 0


class FSObject(object):
    read_only = True

    def stat(self):
        try:
            st_ino = self._st_ino
        except AttributeError:
            global INO_COUNTER
            INO_COUNTER += 1
            st_ino = self._st_ino = INO_COUNTER
        st_dev = 1
        st_nlink = 1
        st_size = self.getsize()
        st_mode = self.kind
        st_mode |= stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        if self.kind == stat.S_IFDIR:
            st_mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if self.read_only:
            st_uid = 0       # read-only files are virtually owned by root
            st_gid = 0
        else:
            st_uid = UID     # read-write files are owned by this virtual user
            st_gid = GID
        st_atime = ATIME
        st_mtime = MTIME
        st_ctime = CTIME
        return os.stat_result(
            (st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid,
             st_size, st_atime, st_mtime, st_ctime))

    def keys(self):
        raise OSError(errno.ENOTDIR, self)

    def open(self):
        raise OSError(errno.EACCES, self)

    def getsize(self):
        return 0


class Dir(FSObject):
    kind = stat.S_IFDIR
    def __init__(self, entries={}):
        self.entries = entries
    def keys(self):
        return self.entries.keys()
    def join(self, name):
        try:
            return self.entries[name]
        except KeyError:
            raise OSError(errno.ENOENT, name)

class RealDir(Dir):
    # If show_dotfiles=False, we pretend that all files whose name starts
    # with '.' simply don't exist.  If follow_links=True, then symlinks are
    # transparently followed (they look like a regular file or directory to
    # the sandboxed process).  If follow_links=False, the subprocess is
    # not allowed to access them at all.
    def __init__(self, path, show_dotfiles=False, follow_links=False):
        self.path = path
        self.show_dotfiles = show_dotfiles
        self.follow_links  = follow_links
    def __repr__(self):
        return '<RealDir %s>' % (self.path,)
    def keys(self):
        names = os.listdir(self.path)
        if not self.show_dotfiles:
            names = [name for name in names if not name.startswith('.')]
        return names
    def join(self, name):
        if name.startswith('.') and not self.show_dotfiles:
            raise OSError(errno.ENOENT, name)
        path = os.path.join(self.path, name)
        if self.follow_links:
            st = os.stat(path)
        else:
            st = os.lstat(path)
        if stat.S_ISDIR(st.st_mode):
            return RealDir(path, show_dotfiles = self.show_dotfiles,
                                 follow_links  = self.follow_links)
        elif stat.S_ISREG(st.st_mode):
            return RealFile(path)
        else:
            # don't allow access to symlinks and other special files
            raise OSError(errno.EACCES, path)

class File(FSObject):
    kind = stat.S_IFREG
    def __init__(self, data=''):
        self.data = data
    def getsize(self):
        return len(self.data)
    def open(self):
        import cStringIO
        return cStringIO.StringIO(self.data)

class RealFile(File):
    def __init__(self, path):
        self.path = path
    def __repr__(self):
        return '<RealFile %s>' % (self.path,)
    def getsize(self):
        return os.stat(self.path).st_size
    def open(self):
        try:
            return open(self.path, "rb")
        except IOError, e:
            raise OSError(e.errno, "open failed")
