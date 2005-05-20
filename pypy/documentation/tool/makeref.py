
import py
py.magic.autopath()
import pypy
pypydir = py.path.local(pypy.__file__).dirpath()
distdir = pypydir.dirpath() 
dist_url = 'http://codespeak.net/svn/pypy/dist/' 

docdir = pypydir.join('documentation') 
reffile = pypydir.join('documentation', '_ref.txt') 

linkrex = py.std.re.compile('`(\S+)`_')

name2target = {}
def addlink(linkname, linktarget): 
    assert linkname and linkname != '/'
    if linktarget in name2target: 
        if linkname in name2target[linktarget]: 
            return
    name2target.setdefault(linktarget, []).append(linkname)

for textfile in docdir.visit(lambda x: x.ext == '.txt', 
                             lambda x: x.check(dotfile=0)): 
    for linkname in linkrex.findall(textfile.read()): 
        if '/' not in linkname: 
            continue
        for startloc in ('', 'pypy'): 
            cand = distdir.join(startloc, linkname)
            if cand.check(): 
                target = dist_url + cand.relto(distdir)
                addlink(linkname, target) 
                break
        else: 
            print "WARNING %s: link %r may be bogus" %(textfile, linkname) 

items = name2target.items() 
items.sort() 

lines = []
for linktarget, linknamelist in items: 
    for linkname in linknamelist[:-1]: 
        lines.append(".. _`%s`:" % linkname)
    lines.append(".. _`%s`: %s" %(linknamelist[-1], linktarget))

reffile.write("\n".join(lines))
print "wrote %d references to %r" %(len(lines), reffile)
#print "last ten lines"
#for x in lines[-10:]: print x
