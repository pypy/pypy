
import py
py.magic.autopath()
import pypy
pypydir = py.path.local(pypy.__file__).dirpath()
distdir = pypydir.dirpath() 
issue_url = 'http://codespeak.net/issue/pypy-dev/' 

import urllib2, posixpath


possible_start_dirs = [
    distdir,
    distdir.join('pypy'),
    # for now, let the jit links point to the oo-jit branch
    'http://codespeak.net/svn/pypy/branch/oo-jit',
    'http://codespeak.net/svn/pypy/branch/oo-jit/pypy',
    ]

def makeref(docdir):
    reffile = docdir.join('_ref.txt') 

    linkrex = py.std.re.compile('`(\S+)`_')

    name2target = {}
    def addlink(linkname, linktarget): 
        assert linkname and linkname != '/'
        if linktarget in name2target: 
            if linkname in name2target[linktarget]: 
                return
        name2target.setdefault(linktarget, []).append(linkname)

    for textfile in docdir.listdir():  # for subdirs, see below
        if textfile.ext != '.txt':
            continue
        for linkname in linkrex.findall(textfile.read()): 
            if '/' in linkname: 
                for startdir in possible_start_dirs:
                    if isinstance(startdir, str):
                        assert startdir.startswith('http://')
                        target = posixpath.join(startdir, linkname)
                        try:
                            urllib2.urlopen(target).close()
                        except urllib2.HTTPError:
                            continue
                    else:
                        cand = startdir.join(linkname)
                        if not cand.check():
                            continue
                        assert cand.relto(distdir)
                        dotdots = 0
                        p = docdir
                        while p != distdir:
                            p = p.dirpath()
                            dotdots += 1
                        target = '../' * dotdots + cand.relto(distdir)
                    addlink(linkname, target) 
                    break
                else: 
                    print "WARNING %s: link %r may be bogus" %(textfile, linkname) 
            elif linkname.startswith('issue'): 
                addlink(linkname, issue_url+linkname)

    items = name2target.items() 
    items.sort() 

    lines = []
    for linktarget, linknamelist in items: 
        linknamelist.sort()
        for linkname in linknamelist[:-1]: 
            lines.append(".. _`%s`:" % linkname)
        lines.append(".. _`%s`: %s" %(linknamelist[-1], linktarget))

    lines.append('')
    reffile.write("\n".join(lines))
    print "wrote %d references to %r" %(len(lines), reffile)
    #print "last ten lines"
    #for x in lines[-10:]: print x


# We need to build a new _ref.txt for each directory that uses it, because
# they differ in the number of "../" that they need in the link targets...
makeref(pypydir.join('doc'))
makeref(pypydir.join('doc').join('jit'))
