"""

svn-Command based Implementation of a Subversion WorkingCopy Path.

  SvnWCCommandPath  is the main class. 

  SvnWC is an alias to this class. 

"""

import os, sys, time, re
from py import path
import py 
from py.__impl__.path import common 
from py.__impl__.path.svn import cache
from py.__impl__.path.svn import svncommon 

DEBUG = 0

class SvnWCCommandPath(common.FSPathBase):
    sep = os.sep

    def __new__(cls, wcpath=None): 
        self = object.__new__(cls)
        self.localpath = path.local(wcpath)
        return self

    strpath = property(lambda x: str(x.localpath), None, None, "string path")

    def __eq__(self, other):
        return self.localpath == getattr(other, 'localpath', None) 

    def _geturl(self):
        if getattr(self, '_url', None) is None:
            info = self.info()
            self._url = info.url #SvnPath(info.url, info.rev)
        assert isinstance(self._url, str)
        return self._url

    def dumpobj(self, obj):
        return self.localpath.dumpobj(obj)

    def svnurl(self):
        """ return current SvnPath for this WC-item. """
        info = self.info()
        return path.svnurl(info.url) 

    url = property(_geturl, None, None, "url of this WC item")

    def __repr__(self):
        return "svnwc(%r)" % (self.strpath) # , self._url)

    def __str__(self):
        return str(self.localpath)

    def _svn(self, cmd, *args):
        l = ['svn %s' % cmd]
        args = map(lambda x: '"%s"' % x, args)
        l.extend(args)
        l.append(self.strpath)
        # try fixing the locale because we can't otherwise parse
        string = svncommon.fixlocale() + " ".join(l)
        if DEBUG:
            print "execing", string
        out = py.process.cmdexec(string)
        return out

    def checkout(self, url=None, rev = None): 
        """ checkout from url to local wcpath. """
        if url is None:
            url = self.url
        if rev is None or rev == -1:
            self._svn('co', url)
        else:
            self._svn('co -r %s' % rev, url)

    def update(self, rev = 'HEAD'):
        """ update working copy item to given revision. (None -> HEAD). """
        self._svn('up -r %s' % rev)

    def write(self, content):
        """ write content into local filesystem wc. """
        self.localpath.write(content)

    def dirpath(self, *args):
        """ return the directory Path of the current Path. """
        return self.__class__(self.localpath.dirpath(*args))

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
            p.add()
            return p
        except:
            error_enhance(sys.exc_info())

    def mkdir(self, *args):
        if args:
            return self.join(*args).mkdir()
        else:
            self._svn('mkdir')
            return self

    def add(self):
        self._svn('add')

    def remove(self, rec=1, force=1): 
        """ remove a file or a directory tree. 'rec'ursive is 
            ignored and considered always true (because of 
            underlying svn semantics. 
        """
        flags = []
        if force:
            flags.append('--force')
        self._svn('remove', *flags)

    def copy(self, target):
        py.process.cmdexec("svn copy %s %s" %(str(self), str(target)))

    def rename(self, target):
        py.process.cmdexec("svn move --force %s %s" %(str(self), str(target)))

    def status(self, updates=0, rec=0):
        """ return (collective) Status object for this file. """
        # http://svnbook.red-bean.com/book.html#svn-ch-3-sect-4.3.1 
        #             2201     2192        jum   test
        if rec:
            rec= ''
        else:
            rec = '--non-recursive'

        if updates:
            updates = '-u'
        else:
            updates = ''

        update_rev = None

        out = self._svn('status -v %s %s' % (updates, rec))
        rootstatus = WCStatus(self)
        rex = re.compile(r'\s+(\d+|-)\s+(\S+)\s+(\S+)\s+(.*)')
        for line in out.split('\n'):
            if not line.strip():
                continue
            #print "processing %r" % line
            flags, rest = line[:8], line[8:]
            # first column
            c0,c1,c2,c3,c4,x5,x6,c7 = flags
            #if '*' in line:
            #    print "flags", repr(flags), "rest", repr(rest)

            if c0 in '?XI':
                fn = line.split(None, 1)[1]
                if c0 == '?':
                    wcpath = self.join(fn, abs=1)
                    rootstatus.unknown.append(wcpath)
                elif c0 == 'X':
                    wcpath = self.__class__(self.localpath.join(fn, abs=1))
                    rootstatus.external.append(wcpath)
                elif c0 == 'I':
                    wcpath = self.join(fn, abs=1)
                    rootstatus.ignored.append(wcpath)
                
                continue

            #elif c0 in '~!' or c4 == 'S':
            #    raise NotImplementedError("received flag %r" % c0)

            m = rex.match(rest)
            if not m:
                if c7 == '*':
                    fn = rest.strip()
                    wcpath = self.join(fn, abs=1)
                    rootstatus.update_available.append(wcpath)
                    continue
                if line.lower().find('against revision:')!=-1:
                    update_rev = int(rest.split(':')[1].strip())
                    continue
                # keep trying
                raise ValueError, "could not parse line %r" % line 
            else:
                rev, modrev, author, fn = m.groups()
            wcpath = self.join(fn, abs=1)
            #assert wcpath.check()
            if c0 == 'M':
                assert wcpath.check(file=1), "didn't expect a directory with changed content here"
                rootstatus.modified.append(wcpath)
            elif c0 == 'A' or c3 == '+' :
                rootstatus.added.append(wcpath)
            elif c0 == 'D':
                rootstatus.deleted.append(wcpath)
            elif c0 == 'C':
                rootstatus.conflict.append(wcpath)
            elif c0 == '~':
                rootstatus.kindmismatch.append(wcpath)
            elif c0 == '!':
                rootstatus.incomplete.append(wcpath)
            elif not c0.strip():
                rootstatus.unchanged.append(wcpath)
            else:
                raise NotImplementedError("received flag %r" % c0)

            if c1 == 'M':
                rootstatus.prop_modified.append(wcpath)
            if c2 == 'L':
                rootstatus.locked.append(wcpath)
            if c7 == '*':
                rootstatus.update_available.append(wcpath)

            if wcpath == self:
                rootstatus.rev = rev
                rootstatus.modrev = modrev
                rootstatus.author = author
                if update_rev:
                    rootstatus.update_rev = update_rev
                continue
        return rootstatus

    def diff(self, rev=None):
        if rev is None:
            out = self._svn('diff')
        else:
            out = self._svn('diff -r %d' % rev)
        return out

    def commit(self, message=None):
        if message:
            self._svn('commit -m %r' % message)
        else:
            os.system(svncommon.fixlocale()+
                      'svn commit %r' % (self.strpath))
        try:
            del cache.info[self]
        except KeyError:
            pass

    def propset(self, propname, value, *args):
        self._svn('propset', propname, value, *args)

    def propget(self, name):
        res = self._svn('propget', name)
        return res[:-1] # strip trailing newline

    def propdel(self, name):
        res = self._svn('propdel', name)
        return res[:-1] # strip trailing newline

    def proplist(self, rec=0):
        if rec:
            res = self._svn('proplist -R')
            return make_recursive_propdict(self, res)
        else:
            res = self._svn('proplist')
            lines = res.split('\n')
            lines = map(str.strip, lines[1:])
            return svncommon.PropListDict(self, lines)
    
    def revert(self, rec=0):
        if rec:
            result = self._svn('revert -R')
        else:
            result = self._svn('revert')
        return result

    def new(self, **kw):
        if kw:
            localpath = self.localpath.new(**kw)
        else:
            localpath = self.localpath
        return self.__class__(localpath) 
        
    def join(self, *args, **kwargs):
        """ return a new Path (with the same revision) which is composed 
            of the self Path followed by 'args' path components.
        """
        if not args:
            return self
        localpath = self.localpath.join(*args, **kwargs)
        return self.__class__(localpath)

    def info(self, usecache=1):
        """ return an Info structure with svn-provided information. """
        info = usecache and cache.info.get(self) 
        if not info:
            try:
                output = self._svn('info')
            except py.process.cmdexec.Error, e:
                if e.err.find('Path is not a working copy directory') != -1:
                    raise path.NotFound, e.err
                raise
            if output.find('Not a versioned resource') != -1:
                raise path.NotFound, output
            info = InfoSvnWCCommand(path.local(self.strpath), output)
            cache.info[self] = info
        self.rev = info.rev
        return info

    def listdir(self, fil=None, sort=None):
        """ return a sequence of Paths.  

        listdir will return either a tuple or a list of paths
        depending on implementation choices. 
        """
        if isinstance(fil, str):
            fil = common.fnmatch(fil)
        # XXX unify argument naming with LocalPath.listdir
        def notsvn(path):
            return not path.get('basename') == '.svn' 

        paths = []
        for localpath in self.localpath.listdir(notsvn):
            p = self.__class__(localpath) 
            paths.append(p)

        if fil or sort:
            paths = filter(fil, paths)
            paths = isinstance(paths, list) and paths or list(paths)
            if callable(sort):
                paths.sort(sort)
            elif sort:
                paths.sort()
        return paths

    def open(self, mode='r'):
        return open(self.strpath, mode)

    def get(self, spec):
        return self.localpath.get(spec)

    class Checkers(path.local.Checkers):
        def __init__(self, path):
            self.svnwcpath = path
            self.path = path.localpath 
        def versioned(self):
            try:
                s = self.svnwcpath.status()
            except py.process.cmdexec.Error, e:
                if e.err.find('is not a working copy')!=-1:
                    return False
                raise
            else:
                return self.svnwcpath in s.allpath(ignored=0,unknown=0, deleted=0)

    def log(self, rev_start=None, rev_end=1, verbose=False):
        from py.__impl__.path.svn.command import _Head, LogEntry
        assert self.check()   # make it simpler for the pipe
        rev_start = rev_start is None and _Head or rev_start
        rev_end = rev_end is None and _Head or rev_end

        if rev_start is _Head and rev_end == 1:
                rev_opt = ""
        else:
            rev_opt = "-r %s:%s" % (rev_start, rev_end)
        verbose_opt = verbose and "-v" or ""
        s = svncommon.fixlocale()
        xmlpipe =  os.popen(s+'svn log --xml %s %s "%s"' % (rev_opt, \
            verbose_opt, self.strpath))
        from xml.dom import minidom
        tree = minidom.parse(xmlpipe)
        result = []
        for logentry in filter(None, tree.firstChild.childNodes):
            if logentry.nodeType == logentry.ELEMENT_NODE:
                result.append(LogEntry(logentry))
        return result

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

    def __hash__(self):
        return hash((self.strpath, self.__class__))


class WCStatus:
    attrnames = ('modified','added', 'conflict', 'unchanged', 'external',
                'deleted', 'prop_modified', 'unknown', 'update_available',
                'incomplete', 'kindmismatch', 'ignored'
                )

    def __init__(self, wcpath, rev=None, modrev=None, author=None):
        self.wcpath = wcpath
        self.rev = rev
        self.modrev = modrev
        self.author = author

        for name in self.attrnames:
            setattr(self, name, [])

    def allpath(self, sort=True, **kw):
        d = {}
        for name in self.attrnames:
            if name not in kw or kw[name]:
                for path in getattr(self, name):
                    d[path] = 1
        l = d.keys()
        if sort:
            l.sort()
        return l

class InfoSvnWCCommand:
    def __init__(self, path, output):
        # Path: test
        # URL: http://codespeak.net/svn/std.path/trunk/dist/std.path/test
        # Repository UUID: fd0d7bf2-dfb6-0310-8d31-b7ecfe96aada
        # Revision: 2151
        # Node Kind: directory
        # Schedule: normal
        # Last Changed Author: hpk
        # Last Changed Rev: 2100
        # Last Changed Date: 2003-10-27 20:43:14 +0100 (Mon, 27 Oct 2003)
        # Properties Last Updated: 2003-11-03 14:47:48 +0100 (Mon, 03 Nov 2003)

        d = {}
        for line in output.split('\n'):
            if not line.strip(): 
                continue
            key, value = line.split(':', 1) 
            key = key.lower().replace(' ', '')
            value = value.strip()
            d[key] = value
        try:
            self.url = d['url']
        except KeyError:
            raise ValueError, "Not a versioned resource %r" % path
        self.kind = d['nodekind'] == 'directory' and 'dir' or d['nodekind']
        self.rev = int(d['revision'])
        self.size = path.size()
        if 'lastchangedrev' in d:
            self.created_rev = int(d['lastchangedrev'])
            self.last_author = d['lastchangedauthor']
            self.mtime = parse_wcinfotime(d['lastchangeddate'])
            self.time = self.mtime * 1000000
        
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

def parse_wcinfotime(timestr):
    # example: 2003-10-27 20:43:14 +0100 (Mon, 27 Oct 2003)
    # XXX honour timezone information
    m = re.match(r'(\d+-\d+-\d+ \d+:\d+:\d+) ([+-]\d+) .*', timestr)
    if not m:
        raise ValueError, "timestring %r does not match" % timestr
    timestr, timezone = m.groups()
    # XXX handle timezone
    parsedtime = time.strptime(timestr, "%Y-%m-%d %H:%M:%S")
    return time.mktime(parsedtime)

def make_recursive_propdict(wcroot, 
                            output, 
                            rex = re.compile("Properties on '(.*)':")):
    """ Return a dictionary of path->PropListDict mappings. """
    lines = filter(None, output.split('\n'))
    pdict = {}
    while lines:
        line = lines.pop(0)
        m = rex.match(line)
        if not m:
            raise ValueError, "could not parse propget-line: %r" % line
        path = m.groups()[0]
        wcpath = wcroot.join(path, abs=1)
        propnames = []
        while lines and lines[0].startswith('  '):
            propname = lines.pop(0).strip()
            propnames.append(propname) 
        assert propnames, "must have found properties!"
        pdict[wcpath] = svncommon.PropListDict(wcpath, propnames)
    return pdict

def error_enhance((cls, error, tb)):
    raise cls, error, tb

