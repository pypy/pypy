
import py
py.path.local(__file__)
import pypy
pypydir = py.path.local(pypy.__file__).dirpath()
distdir = pypydir.dirpath() 
issue_url = 'http://codespeak.net/issue/pypy-dev/' 
bitbucket_url = 'https://bitbucket.org/pypy/pypy/src/default/'

import urllib2, posixpath


def makeref(docdir):
    reffile = docdir.join('_ref.rst') 

    linkrex = py.std.re.compile('`(\S+)`_')

    name2target = {}
    def addlink(linkname, linktarget): 
        assert linkname and linkname != '/'
        if linktarget in name2target: 
            if linkname in name2target[linktarget]: 
                return
        name2target.setdefault(linktarget, []).append(linkname)

    for textfile in docdir.listdir():  # for subdirs, see below
        if textfile.ext != '.rst':
            continue
        content = textfile.read()
        found = False
        for linkname in linkrex.findall(content): 
            if '/' in linkname:
                found = True
                if not linkname.endswith("/") and distdir.join(linkname).check(dir=1):
                    print linkname
                    linkname += "/"
                addlink(linkname, bitbucket_url + linkname)
            elif linkname.startswith('issue'): 
                found = True
                addlink(linkname, issue_url+linkname)
        if found:
            assert ".. include:: _ref.rst" in content, "you need to include _ref.rst in %s" % (textfile, )

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
