"""
module with base functionality for std.path package

"""
from __future__ import generators
import sys
import py 

def checktype(pathinstance, kw):
    names = ('local', 'svnwc', 'svnurl', 'py', 'fspy') 
    for name,value in kw.items():
        if name in names:
            cls = getattr(py.path, name) 
            if bool(isinstance(pathinstance, cls)) ^ bool(value):
                return False
            del kw[name]
    return True

class checker:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    def __call__(self, p):
        return p.check(**self.kwargs)
    
class Checkers:
    _depend_on_existence = 'exists', 

    def __init__(self, path):
        self.path = path

    def exists(self):
        raise NotImplementedError

    def basename(self, arg):
        return self.path.basename == arg

    def basestarts(self, arg):
        return self.path.basename.startswith(arg)

    def relto(self, arg):
        return self.path.relto(arg)

    def fnmatch(self, arg):
        return fnmatch(arg)(self.path)

    def endswith(self, arg):
        return str(self.path).endswith(arg)

    def _evaluate(self, kw):
        for name, value in kw.items():
            invert = False 
            meth = None
            try:
                meth = getattr(self, name)
            except AttributeError:
                if name[:3] == 'not':
                    invert = True
                    try: 
                        meth = getattr(self, name[3:]) 
                    except AttributeError: 
                        pass
            if meth is None:
                raise TypeError, "no %r checker available for %r" % (name, self.path)
            try:
                if meth.im_func.func_code.co_argcount > 1:
                    if (not meth(value)) ^ invert:
                        return False
                else:
                    if bool(value) ^ bool(meth()) ^ invert:
                        return False
            except (py.path.NotFound, py.path.NoDirectory): 
                for name in self._depend_on_existence: 
                    if name in kw:
                        if kw.get(name):
                            return False
                    name = 'not' + name 
                    if name in kw:
                        if not kw.get(name):
                            return False
        return True

class PathBase(object):
    """ shared implementation for filesystem path objects."""
    Checkers = Checkers
    from py.path import NotFound 

    def check(self, **kw):
        if kw:
            kw = kw.copy()
            if not checktype(self, kw):
                return False
        else:
            kw = {'exists' : 1}
        return self.Checkers(self)._evaluate(kw)

    def __iter__(self):
        for i in self.listdir():
            yield i

    def __contains__(self, other):
        if type(other) is str:
            for x in self:
                if x.basename == other:
                    return True
        else:
            if other in self.listdir():
                return True
        return False

    def basename(self):
        return self.get('basename')
    basename = property(basename, None, None, 'basename part of path') 

    def parts(self, reverse=False): 
        """ return a root-first list of all ancestor directories 
            plus the path itself.
        """
        current = self
        l = [self]
        while 1:
            last = current
            current = current.dirpath()
            if last == current:
                break 
            l.insert(0, current) 
        if reverse:
            l.reverse()
        return l

    def common(self, other):
        """ return the common part shared with the other path
            or None if there is no common part. 
        """
        last = None
        for x, y in zip(self.parts(), other.parts()):
            print "x", x
            print "y", y
            if x != y:
                return last 
            last = x
        return last

    def __cmp__(self, other):
        try:
            try:
                return cmp(self.strpath, other.strpath)
            except AttributeError:
                return cmp(str(self), str(other)) # self.path, other.path)
        except:
            self._except(sys.exc_info())

    def __repr__(self):
        return repr(str(self))

    def _except(self, excinfo):
        """ default exception handling is to reraise it. """
        raise excinfo[0], excinfo[1], excinfo[2]

    def visit(self, fil=None, rec=None, ignore=None): 
        if isinstance(fil, str):
            fil = fnmatch(fil)
        if isinstance(rec, str):
            rec = fnmatch(fil)
        if ignore:
            try:
                dirlist = self.listdir()
            except ignore:
                return 
        else:
            dirlist = self.listdir()
        checkdir = py.path.checker(dir=1)
        reclist = []
        for p in dirlist: 
            if fil is None or fil(p):
                yield p
            if checkdir(p) and (rec is None or rec(p)):
                reclist.append(p)

        for p in reclist:
            for i in p.visit(fil, rec, ignore=ignore):
                yield i

class fnmatch:
    def __init__(self, pattern):
        self.pattern = pattern
    def __call__(self, path):
        """return true if the basename/fullname matches the glob-'pattern'.

        *       matches everything
        ?       matches any single character
        [seq]   matches any character in seq
        [!seq]  matches any char not in seq

        if the pattern contains a path-separator then the full path
        is used for pattern matching and a '*' is prepended to the 
        pattern. 

        if the pattern doesn't contain a path-separator the pattern
        is only matched against the basename. 
        """
        pattern = self.pattern
        if pattern.find(path.sep) == -1:
            name = path.get('basename')
        else:
            name = str(path) # path.strpath # XXX svn? 
            pattern = '*' + path.sep + pattern
        from fnmatch import fnmatch
        return fnmatch(name, pattern)


class FSCheckers(Checkers):
    _depend_on_existence = Checkers._depend_on_existence+('dir', 'file')

    def dir(self):
        raise NotImplementedError

    def file(self):
        raise NotImplementedError

    def dotfile(self):
        return self.path.basename.startswith('.')

    def ext(self, arg):
        if not arg.startswith('.'):
            arg = '.' + arg
        return self.path.get('ext') == arg

class FSPathBase(PathBase): 
    """ shared implementation for filesystem path objects."""
    Checkers = FSCheckers
    from py.path import NotFound 

    def __div__(self, other):
        return self.join(str(other))

    def ext(self):
        return self.get('ext')
    ext = property(ext, None, None, 'extension part of path') 

    def purebasename(self):
        return self.get('purebasename')
    purebasename = property(purebasename, None, None, 'basename without extension')

    def read(self, num=-1):
        #""" read up to 'num' bytes. (if num==-1 then read all)"""
        try:
            f = self.open('rb')
            try:
                return f.read(num)
            finally:
                f.close()
        except:
            self._except(sys.exc_info())

    def readlines(self, cr=1):
        if not cr:
            content = self.read()
            return content.split('\n')
        else:
            f = self.open('r')
            try:
                return f.readlines()
            finally:
                f.close()

    def loadobj(self):
        """ return object unpickled from self.read() """
        try:
            f = self.open('rb')
            try:
                from cPickle import load
                return load(f)
            finally:
                f.close()
        except:
            self._except(sys.exc_info())

    def move(self, target):
        if target.relto(self):
            raise py.path.Invalid("cannot move path into a subdirectory of itself") 
        try:
            self.rename(target)
        except py.path.Invalid:
            self.copy(target)    
            self.remove()

