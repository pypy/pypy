"""

module defining a subversion path object based on the external
command 'svn'. 

"""

import os, sys, time, re
from py import path, process
from py.__impl__.path import common 
from py.__impl__.path import error 
from py.__impl__.path.svn import svncommon 

class SvnCommandPath(svncommon.SvnPathBase):
    def __new__(cls, path, rev=None): 
        if isinstance(path, cls): 
            if path.rev == rev:
                return path 
        self = object.__new__(cls)
        self.strpath = path.rstrip('/')
        self.rev = rev
        return self

    def __repr__(self):
        if self.rev == -1:
            return 'svnurl(%r)' % self.strpath 
        else:
            return 'svnurl(%r, %r)' % (self.strpath, self.rev) 

    def _svn(self, cmd, *args):
        if self.rev is None: 
            l = ['svn %s' % cmd]
        else:
            l = ['svn %s -r %d' % (cmd, self.rev)]
        args = map(lambda x: '"%s"' % str(x), args)
        l.extend(args)
        l.append(str(self.strpath))
        # fixing the locale because we can't otherwise parse
        string = svncommon.fixlocale() + " ".join(l)
        #print "execing", string
        out = process.cmdexec(string)
        return out

    def _svnwrite(self, cmd, *args):
        l = ['svn %s' % cmd]
        args = map(lambda x: '"%s"' % str(x), args)
        l.extend(args)
        l.append(str(self.strpath))
        # fixing the locale because we can't otherwise parse
        string = svncommon.fixlocale() + " ".join(l)
        #print "execing", string
        out = process.cmdexec(string)
        return out

    def open(self, mode='r'):
        assert 'w' not in mode and 'a' not in mode, "XXX not implemented for svn cmdline" 
        assert self.check(file=1) # svn cat returns an empty file otherwise
        def popen(cmd):
            return os.popen(cmd)
        if self.rev is None:
            return popen(svncommon.fixlocale() + 
                            'svn cat "%s"' % (self.strpath, ))
        else:
            return popen(svncommon.fixlocale() + 
                            'svn cat -r %s "%s"' % (self.rev, self.strpath))

    def mkdir(self, commit_msg=None):
        if commit_msg:
            self._svnwrite('mkdir', '-m', commit_msg)
        else:
            self._svnwrite('mkdir')

    def copy(self, target, msg='auto'):
        if getattr(target, 'rev', None) is not None: 
            raise path.Invalid("target can't have a revision: %r" % target)
        process.cmdexec("svn copy -m %r %s %s" %(msg, str(self), str(target)))

    def remove(self, rec=1, msg='auto'):
        if self.rev is not None:
            raise path.Invalid("cannot remove revisioned object: %r" % self)
        process.cmdexec("svn rm -m %r %s" %(msg, str(self)))

    def _propget(self, name):
        res = self._svn('propget', name)
        return res[:-1] # strip trailing newline

    def _proplist(self):
        res = self._svn('proplist')
        lines = res.split('\n')
        lines = map(str.strip, lines[1:])
        return svncommon.PropListDict(self, lines)

    def _listdir_nameinfo(self):
        """ return sequence of name-info directory entries of self """
        try:
            res = self._svn('ls', '-v')
        except process.cmdexec.Error, e:
            if e.err.find('non-existent in that revision') != -1:
                raise error.FileNotFound(self, e.err)
            elif e.err.find('not part of a repository')!=-1:
                raise IOError, e.err
            elif e.err.find('Unable to open')!=-1:
                raise IOError, e.err
            elif e.err.lower().find('method not allowed')!=-1:
                raise IOError, e.err
            raise 
        lines = res.split('\n')
        nameinfo_seq = []
        for lsline in lines:
            if lsline:
                info = InfoSvnCommand(lsline)
                nameinfo_seq.append((info._name, info))
        return nameinfo_seq

    def log(self, rev_start=None, rev_end=1, verbose=False):
        assert self.check() #make it simpler for the pipe
        rev_start = rev_start is None and _Head or rev_start
        rev_end = rev_end is None and _Head or rev_end

        if rev_start is _Head and rev_end == 1:
            rev_opt = ""
        else:
            rev_opt = "-r %s:%s" % (rev_start, rev_end)
        verbose_opt = verbose and "-v" or ""
        xmlpipe =  os.popen(svncommon.fixlocale() +
                      'svn log --xml %s %s "%s"' % 
                      (rev_opt, verbose_opt, self.strpath))
        from xml.dom import minidom
        tree = minidom.parse(xmlpipe)
        result = []
        for logentry in filter(None, tree.firstChild.childNodes):
            if logentry.nodeType == logentry.ELEMENT_NODE:
                result.append(LogEntry(logentry))
        return result

#01234567890123456789012345678901234567890123467
#   2256      hpk        165 Nov 24 17:55 __init__.py
#
class InfoSvnCommand:
    #lspattern = re.compile(r'(\D*)(\d*)\s*(\w*)\s*(
    def __init__(self, line):
        # this is a typical line from 'svn ls http://...'
        #_    1127      jum        0 Jul 13 15:28 branch/
        l = [line[:7], line[7:16], line[16:27], line[27:40], line[41:]]
        l = map(str.lstrip, l)

        self._name = l.pop()
        if self._name[-1] == '/':
            self._name = self._name[:-1]
            self.kind = 'dir'
        else:
            self.kind = 'file'
        #self.has_props = l.pop(0) == 'P'
        self.created_rev = int(l[0])
        self.last_author = l[1]
        self.size = l[2] and int(l[2]) or 0
        datestr = l[3]
        self.mtime = parse_time_with_missing_year(datestr)
        self.time = self.mtime * 1000000

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


#____________________________________________________
#
# helper functions
#____________________________________________________
def parse_time_with_missing_year(timestr):
    """ analyze the time part from a single line of "svn ls -v" 
    the svn output doesn't show the year makes the 'timestr'
    ambigous. 
    """
    t_now = time.gmtime()

    tparts = timestr.split()
    month = time.strptime(tparts.pop(0), '%b')[1]
    day = time.strptime(tparts.pop(0), '%d')[2]
    last = tparts.pop(0) # year or hour:minute 
    try:
        year = time.strptime(last, '%Y')[0]
        hour = minute = 0
    except ValueError:
        hour, minute = time.strptime(last, '%H:%M')[3:5]
        year = t_now[0]

        t_result = (year, month, day, hour, minute, 0,0,0,0)
        if t_result > t_now:
            year -= 1
    t_result = (year, month, day, hour, minute, 0,0,0,0)
    return time.mktime(t_result)

class PathEntry:
    def __init__(self, ppart):
        self.strpath = ppart.firstChild.nodeValue.encode('UTF-8')
        self.action = ppart.getAttribute('action').encode('UTF-8')
        if self.action == 'A':
            self.copyfrom_path = ppart.getAttribute('copyfrom-path').encode('UTF-8')
            if self.copyfrom_path:
                self.copyfrom_rev = int(ppart.getAttribute('copyfrom-rev'))

class LogEntry:
    def __init__(self, logentry):
        self.rev = int(logentry.getAttribute('revision'))
        for lpart in filter(None, logentry.childNodes):
            if lpart.nodeType == lpart.ELEMENT_NODE:
                if lpart.nodeName == u'author':
                    self.author = lpart.firstChild.nodeValue.encode('UTF-8')
                elif lpart.nodeName == u'msg':
                    if lpart.firstChild:
                        self.msg = lpart.firstChild.nodeValue.encode('UTF-8')
                    else:
                        self.msg = ''
                elif lpart.nodeName == u'date':
                    #2003-07-29T20:05:11.598637Z
                    timestr = lpart.firstChild.nodeValue.encode('UTF-8')   
                    self.date = svncommon.parse_apr_time(timestr)
                elif lpart.nodeName == u'paths':
                    self.strpaths = []
                    for ppart in filter(None, lpart.childNodes):
                        if ppart.nodeType == ppart.ELEMENT_NODE:
                            self.strpaths.append(PathEntry(ppart))
    def __repr__(self):
        return '<Logentry rev=%d author=%s date=%s>' % (
            self.rev, self.author, self.date)
                            

class _Head:
    def __str__(self):
        return "HEAD"

