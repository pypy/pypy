"""
module with a base subversion path object. 
"""
import os, sys, time, re
from py import path, process
from py.__impl__.path import error
from py.__impl__.path import common

#_______________________________________________________________

class SvnPathBase(common.FSPathBase):
    """ Base implementation for SvnPath implementations. """
    sep = '/'

    def _geturl(self):
        return self.strpath
    url = property(_geturl, None, None, "url of this svn-path.")

    def __str__(self):
        """ return a string representation (including rev-number) """
        return self.strpath 

    def __hash__(self):
        return hash(self.strpath)

    def new(self, **kw):
        """ create a modified version of this path. A 'rev' argument
            indicates a new revision.  
            the following keyword arguments modify various path parts:

              http://host.com/repo/path/file.ext 
              |-----------------------|          dirname
                                        |------| basename
                                        |--|     purebasename
                                            |--| ext
        """
        obj = object.__new__(self.__class__)
        obj.rev = kw.get('rev', self.rev)

        if 'basename' in kw:
            if 'purebasename' in kw or 'ext' in kw:
                raise ValueError("invalid specification")
        else:
            pb = kw.setdefault('purebasename', self.get('purebasename'))
            ext = kw.setdefault('ext', self.get('ext'))
            if ext and not ext.startswith('.'):
                ext = '.' + ext
            kw['basename'] = pb + ext

        kw.setdefault('dirname', self.get('dirname'))
        kw.setdefault('sep', self.sep)
        if kw['basename']: 
            obj.strpath = "%(dirname)s%(sep)s%(basename)s" % kw
        else:
            obj.strpath = "%(dirname)s" % kw
        return obj

    def get(self, spec):
        """ get specified parts of the path.  'arg' is a string
            with comma separated path parts. The parts are returned
            in exactly the order of the specification. 
    
            you may specify the following parts: 

            http://host.com/repo/path/file.ext 
            |-----------------------|          dirname
                                      |------| basename
                                      |--|     purebasename
                                          |--| ext
        """
        res = []
        parts = self.strpath.split(self.sep)
        for name in spec.split(','):
            name = name.strip()
            if name == 'dirname':
                res.append(self.sep.join(parts[:-1]))
            elif name == 'basename':
                res.append(parts[-1])
            else:
                basename = parts[-1]
                i = basename.rfind('.')
                if i == -1:
                    purebasename, ext = basename, ''
                else:
                    purebasename, ext = basename[:i], basename[i:]
                if name == 'purebasename':
                    res.append(purebasename)
                elif name == 'ext':
                    res.append(ext)
                else:
                    raise NameError, "Don't know part %r" % name
        if len(res) == 1:
            return res[0]
        elif len(res) == 0:
            return None
        return res

    def __eq__(self, other):
        """ return true if path and rev attributes each match """
        return (str(self) == str(other) and 
               (self.rev == other.rev or self.rev == other.rev))

    def __ne__(self, other):
        return not self == other

    def join(self, *args):
        """ return a new Path (with the same revision) which is composed 
            of the self Path followed by 'args' path components.
        """
        if not args:
            return self
        
        args = tuple([arg.strip(self.sep) for arg in args])
        parts = (self.strpath, ) + args
        newpath = self.__class__(self.sep.join(parts), self.rev)
        return newpath

    def dirpath(self, *args):
        """ return the directory Path of the current Path. """
        return self.new(basename='').join(*args)

    def propget(self, name):
        """ return the content of the given property. """
        value = self._propget(name)
        return value

    def proplist(self):
        """ list all property names. """
        content = self._proplist()
        return content

    # XXX unify argument naming with LocalPath.listdir
    def listdir(self, fil=None, sort=None):
        """ return a sequence of Paths.  

        listdir will return either a tuple or a list of paths
        depending on implementation choices. 
        """
        if isinstance(fil, str):
            fil = common.fnmatch(fil)
        nameinfo_seq = self._listdir_nameinfo() 
        paths = self._make_path_tuple(nameinfo_seq)

        if fil or sort:
            paths = filter(fil, paths)
            paths = isinstance(paths, list) and paths or list(paths)
            if callable(sort):
                paths.sort(sort)
            elif sort:
                paths.sort()
        return paths

    def info(self):
        """ return an Info structure with svn-provided information. """
        parent = self.dirpath()
        nameinfo_seq = parent._listdir_nameinfo() 
        bn = self.basename
        for name, info in nameinfo_seq:
            if name == bn: 
                return info 
        raise error.FileNotFound(self)

    def size(self):
        """ Return the size of the file content of the Path. """
        return self.info().size

    def mtime(self):
        """ Return the last modification time of the file. """
        return self.info().mtime

    def relto(self, rel):
        """ Return a string which is the relative part of the Path to 'rel'. 

        If the Path is not relative to the given base, return an empty string. 
        """
        relpath = rel.strpath
        if self.strpath.startswith(relpath):
            return self.strpath[len(relpath)+1:]
        return ""


    # shared help methods

    def _make_path_tuple(self, nameinfo_seq):
        """ return a tuple of paths from a nameinfo-tuple sequence.
        """
        #assert self.rev is not None, "revision of %s should not be None here" % self
        res = []
        for name, info in nameinfo_seq:
            child = self.join(name)
            res.append(child)
        return tuple(res)


    #def _childmaxrev(self):
    #    """ return maximum revision number of childs (or self.rev if no childs) """
    #    rev = self.rev
    #    for name, info in self._listdir_nameinfo():
    #        rev = max(rev, info.created_rev)
    #    return rev

    #def _getlatestrevision(self):
    #    """ return latest repo-revision for this path. """
    #    url = self.strpath 
    #    path = self.__class__(url, None)
    #
    #    # we need a long walk to find the root-repo and revision
    #    while 1:
    #        try:
    #            rev = max(rev, path._childmaxrev())
    #            previous = path
    #            path = path.dirpath()
    #        except (IOError, process.cmdexec.Error):
    #            break
    #    if rev is None: 
    #        raise IOError, "could not determine newest repo revision for %s" % self
    #    return rev

    class Checkers(common.FSCheckers):
        def _info(self):
            try:
                return self._infocache
            except AttributeError:
                self._infocache = self.path.info()
                return self._infocache

        def dir(self):
            try:
                return self._info().kind == 'dir'
            except IOError:
                return self._listdirworks()

        def _listdirworks(self):
            try:
                self.path.listdir()
            except error.FileNotFound:
                return False
            else:
                return True

        def file(self):
            try:
                return self._info().kind == 'file'
            except (IOError, error.FileNotFound):
                return False

        def exists(self):
            try:
                return self._info()
            except IOError:
                return self._listdirworks()

def parse_apr_time(timestr):
    i = timestr.rfind('.')
    if i == -1:
        raise ValueError, "could not parse %s" % timestr
    timestr = timestr[:i]
    parsedtime = time.strptime(timestr, "%Y-%m-%dT%H:%M:%S")
    return time.mktime(parsedtime)

class PropListDict(dict):
    """ a Dictionary which fetches values (InfoSvnCommand instances) lazily"""
    def __init__(self, path, keynames):
        dict.__init__(self, [(x, None) for x in keynames])
        self.path = path

    def __getitem__(self, key):
        value = dict.__getitem__(self, key)
        if value is None:
            value = self.path.propget(key)
            dict.__setitem__(self, key, value)
        return value

def fixlocale():
    if sys.platform != 'win32':
        return 'LC_ALL=C '
    return ''
