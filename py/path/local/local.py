"""
specialized local path implementation. 

This Path implementation offers some methods like chmod(), owner() 
and so on that may only make sense on unix. 

"""
import sys, os, stat
import py 
from py.__impl__.path import error 
from py.__impl__.path import common 

if sys.platform == 'win32':
    from py.__impl__.path.local.win import WinMixin as PlatformMixin 
else:
    from py.__impl__.path.local.posix import PosixMixin as PlatformMixin 

class LocalPath(common.FSPathBase, PlatformMixin):
    """ the fully specialized local path implementation. 
    (including symbolic links and all kinds of stuff.)
    """
    sep = os.sep
    class Checkers(common.FSCheckers):
        def _stat(self):
            try:
                return self._statcache
            except AttributeError:
                try:
                    self._statcache = self.path.stat()
                except error.NestedLink: 
                    self._statcache = self.path.lstat() 
                return self._statcache
           
        def dir(self):
            return stat.S_ISDIR(self._stat().st_mode)

        def file(self):
            return stat.S_ISREG(self._stat().st_mode)

        def exists(self):
            return self._stat()

        def link(self):
            st = self.path.lstat()
            return stat.S_ISLNK(st.st_mode)

    def __new__(cls, path=None):
        """ Initialize and return a local Path instance. 

        Path can be relative to the current directory.
        If it is None then the current working directory is taken.
        Note that Path instances always carry an absolute path.
        Note also that passing in a local path object will simply return 
        the exact same path object.
        """
        if isinstance(path, cls): 
            if path.__class__ == cls:
                return path
            path = path.strpath
        # initialize the path
        self = object.__new__(cls)
        if path is None:
            self.strpath = os.getcwd()
        elif not path:
            raise ValueError(
                "can only pass None, Path instances "
                "or non-empty strings to LocalPath")
        else:
            self.strpath = os.path.abspath(os.path.normpath(str(path)))
        assert isinstance(self.strpath, str)
        return self

    def __hash__(self):
        return hash(self.strpath)

    def _except(self, excinfo):
        return error.error_enhance(excinfo) 

    def new(self, **kw):
        """ create a modified version of this path.
            the following keyword arguments modify various path parts:

              a:/some/path/to/a/file.ext 
              ||                            drive
                |-------------|             dirname 
                                |------|    basename
                                |--|        purebasename
                                    |--|    ext
        """
        obj = object.__new__(self.__class__)
        if 'basename' in kw:
            if 'purebasename' in kw or 'ext' in kw:
                raise ValueError("invalid specification")
        else:
            pb = kw.setdefault('purebasename', self.get('purebasename'))
            if 'ext' in kw:
                ext = kw['ext']
                if ext and not ext.startswith('.'):
                    ext = '.' + ext
            else:
                ext = self.get('ext')
            kw['basename'] = pb + ext

        kw.setdefault('drive', self.get('drive'))
        kw.setdefault('dirname', self.get('dirname'))

        kw.setdefault('sep', self.sep)
        obj.strpath = os.path.normpath(
            "%(drive)s%(dirname)s%(sep)s%(basename)s" % kw)
        return obj

    def get(self, spec):
        """ return a sequence of specified path parts.  'spec' is
            a comma separated string containing path part names. 
            according to the following convention: 
            a:/some/path/to/a/file.ext 
            ||                            drive
              |-------------|             dirname 
                              |------|    basename
                              |--|        purebasename
                                  |--|    ext
        """
        res = []
        parts = self.strpath.split(self.sep)
        
        args = filter(None, spec.split(',') )
        append = res.append
        for name in args:
            if name == 'drive':
                append(parts[0])
            elif name == 'dirname':
                append(self.sep.join(['']+parts[1:-1]))
            else:
                basename = parts[-1]
                if name == 'basename':
                    append(basename)
                else:
                    i = basename.rfind('.')
                    if i == -1:
                        purebasename, ext = basename, ''
                    else:
                        purebasename, ext = basename[:i], basename[i:]
                    if name == 'purebasename':
                        append(purebasename)
                    elif name == 'ext':
                        append(ext)
                    else:
                        raise ValueError, "invalid part specification %r" % name

        if len(res) == 1:
            return res[0]
        elif len(res) == 0:
            return None
        else:
            return res

    def join(self, *args, **kwargs):
        """ return a new path by appending all 'args' as path
        components.  if abs=1 is used start from root if any if the args
        is an absolute path.
        """
        if not args:
            return self
        args = (self.strpath,) + args 
        if kwargs.get('abs', 0):
            for i in range(len(args)-1, 0, -1):
                if os.path.isabs(str(args[i])):
                    args = map(str, args[i:])
                    break
        obj = self.new()
        obj.strpath = os.path.normpath(self.sep.join(args))
        return obj

    def __eq__(self, other):
        return str(self) == str(other)

    def dirpath(self, *args):
        x = self.new(basename='')
        if args:
            return x.join(*args)
        else:
            return x 

    def open(self, mode='r'):
        """ return an opened file with the given mode. """
        try:
            return open(self.strpath, mode)
        except:
            self._except(sys.exc_info())

    def listdir(self, fil=None, sort=None):
        """ list directory contents, possibly filter by the given fil func
            and possibly sorted.
        """
        if isinstance(fil, str):
            fil = common.fnmatch(fil)
        res = []
        try:
            for name in os.listdir(self.strpath):
                childurl = self.join(name)
                if fil is None or fil(childurl):
                    res.append(childurl)
        except:
            self._except(sys.exc_info())
        if callable(sort):
            res.sort(sort)
        elif sort:
            res.sort()
        return res

    def size(self):
        """ return size of the underlying file object """
        return self.stat().st_size

    def mtime(self):
        """ return last modification time of the path. """
        return self.stat().st_mtime

    def relto(self, relpath):
        """ return a string which is the relative part of the path
        to the given 'relpath' (which might be a string or a path object).
        """
        relpath = str(relpath)
        if self.strpath.startswith(relpath):
            return self.strpath[len(relpath)+1:]
        return ""

    def remove(self, rec=1):
        """ remove a file or directory (or a directory tree if rec=1).  """
        try:
            if self.check(dir=1, link=0):
                if rec:
                    import shutil
                    #def call(*args):
                    #    print args

                    shutil.rmtree(self.strpath) 
                    #, onerror=call)
                else:
                    os.rmdir(self.strpath)
            else:
                os.remove(self.strpath)
        except:
            self._except(sys.exc_info())

    def copy(self, target, archive=False):
        try:
            assert not archive 
            if self.check(file=1):
                if target.check(dir=1):
                    target = target.join(self.basename)
                assert self!=target
                copychunked(self, target)
            else:
                target.ensure(dir=1)
                def rec(p):
                    return p.check(link=0)
                for x in self.visit(rec=rec): 
                    relpath = x.relto(self) 
                    newx = target.join(relpath)
                    if x.check(link=1):
                        newx.mksymlinkto(x.readlink())
                    elif x.check(file=1):
                        copychunked(x, newx)
                    elif x.check(dir=1):
                        newx.ensure(dir=1) 
        except:
            self._except(sys.exc_info())

    def rename(self, target):
        try:
            os.rename(str(self), str(target))
        except:
            self._except(sys.exc_info())

    def dumpobj(self, obj):
        """ pickle object into path location"""
        try:
            f = self.open('wb')
            try:
                from cPickle import dump
                dump(obj, f)
            finally:
                f.close()
        except: 
            self._except(sys.exc_info())

    def mkdir(self, *args):
        """ create & return the directory joined with args. """
        p = self.join(*args)
        try:
            os.mkdir(str(p))
        except:
            self._except(sys.exc_info())
        return p

    def write(self, content):
        """ write string content into path. """
        f = self.open('wb')
        try:
            f.write(content)
        finally:
            f.close()

    def _ensuredirs(self):
        parent = self.dirpath()
        if parent.check(dir=0):
            parent._ensuredirs()
        if self.check(dir=0):
            self.mkdir()
        return self

    def ensure(self, *args, **kwargs):
        """ ensure that an args-joined path exists (by default as 
            a file). if you specify a keyword argument 'directory=True'
            then the path is forced  to be a directory path. 
        """
        try:
            p = self.join(*args)
            if kwargs.get('dir', 0):
                return p._ensuredirs()
            parent = p.dirpath()
            parent._ensuredirs()
            p.write("")
            return p
        except:
            self._except(sys.exc_info())

    def stat(self):
        """ Return an os.stat() tuple. """
        try:
            return os.stat(self.strpath)
        except:
            self._except(sys.exc_info()) 

    def lstat(self):
        """ Return an os.lstat() tuple. """
        try:
            return os.lstat(self.strpath)
        except:
            self._except(sys.exc_info()) 

    # xlocal implementation
    def setmtime(self, mtime=None):
        """ set modification time for the given path.  if 'mtime' is None
        (the default) then the file's mtime is set to current time. 

        Note that the resolution for 'mtime' is platform dependent.
        """
        if mtime is None:
            return os.utime(self.strpath, mtime)
        try:
            return os.utime(self.strpath, (-1, mtime))
        except OSError, e:
            if e.errno != 22:
                self._except(sys.exc_info())
                raise
            return os.utime(self.strpath, (self.atime(), mtime))

    def chdir(self):
        """ change directory to self and return old current directory """
        old = self.__class__()
        os.chdir(self.strpath)
        return old

    def realpath(self):
        """ return a new path which contains no symbolic links."""
        return self.__class__(os.path.realpath(self.strpath))

    def atime(self):
        """ return last access time of the path. """
        return self.stat().st_atime

    def __repr__(self):
        return 'local(%r)' % self.strpath

    def __str__(self):
        """ return string representation of the Path. """
        return self.strpath


    #"""
    #special class constructors for local filesystem paths
    #"""
    def get_temproot(cls):
        """ return the system's temporary directory (where tempfiles are usually created in)"""
        p = cls.mkdtemp()
        try:
            return p.dirpath()
        finally:
            p.remove()
    get_temproot = classmethod(get_temproot) 
        
    def mkdtemp(cls):
        """ return a Path object pointing to a fresh new temporary directory
        (which we created ourself).  
        """
        import tempfile
        tries = 10
        for i in range(tries):
            dname = tempfile.mktemp()
            dpath = cls(tempfile.mktemp()) 
            try:
                dpath.mkdir()
            except path.FileExists:
                continue
            return dpath
        raise NotFound, "could not create tempdir, %d tries" % tries
    mkdtemp = classmethod(mkdtemp) 

    def make_numbered_dir(cls, rootdir=None, base = 'session-', keep=3):
        """ return unique directory with a number greater than the current
            maximum one.  The number is assumed to start directly after base. 
            if keep is true directories with a number less than (maxnum-keep)
            will be removed. 
        """
        if rootdir is None:
            rootdir = cls.get_temproot()

        def parse_num(path):
            """ parse the number out of a path (if it matches the base) """
            bn = path.get('basename')
            if bn.startswith(base):
                try:
                    return int(bn[len(base):])
                except TypeError:
                    pass

        # compute the maximum number currently in use with the base
        maxnum = -1
        for path in rootdir.listdir():
            num = parse_num(path)
            if num is not None:
                maxnum = max(maxnum, num)

        # make the new directory 
        udir = rootdir.mkdir(base + str(maxnum+1))

        # prune old directories
        if keep: 
            for path in rootdir.listdir():
                num = parse_num(path)
                if num is not None and num <= (maxnum - keep):
                    path.remove(rec=1)
        return udir
    make_numbered_dir = classmethod(make_numbered_dir)

    #def parentdirmatch(cls, dirname, startmodule=None):
    #    """ ??? """
    #    if startmodule is None:
    #        fn = path.local()
    #    else:
    #        mod = path.py(startmodule) 
    #        fn = mod.getfile()
    #    current = fn.dirpath()
    #    while current != fn:
    #        fn = current
    #        if current.basename() == dirname:
    #            return current
    #        current = current.dirpath()
    #parentdirmatch = classmethod(parentdirmatch)

def copychunked(src, dest): 
    chunksize = 524288 # bytes
    fsrc = src.open('rb')
    try:
        fdest = dest.open('wb')
        try:
            while 1:
                buf = fsrc.read(chunksize)
                if not buf:
                    break
                fdest.write(buf)
        finally:
            fdest.close()
    finally:
        fsrc.close()
