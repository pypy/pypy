
import autopath
import py

log = py.log.Producer("log")
logexec = py.log.Producer("exec")

import os

BASEURL = "file:///svn/pypy/release/1.0.x"
DDIR = py.path.local('/www/codespeak.net/htdocs/download/pypy')

def usage():
    print "usage: %s [-tag .<micro>] versionbasename" %(py.std.sys.argv[0])
    raise SystemExit, 1

def cexec(cmd): 
    logexec(cmd)
    return py.process.cmdexec(cmd) 

def maketargz(target):
    targz = target + ".tar.gz"
    basename = target.basename 
    old = target.dirpath().chdir() 
    try:
        out = cexec("tar zcvf %(targz)s %(basename)s" % locals())
    finally:
        old.chdir()
    assert targz.check(file=1)
    assert targz.size() > 0
    return targz 

def maketarbzip(target):
    targz = target + ".tar.bz2" 
    basename = target.basename 
    old = target.dirpath().chdir() 
    try:
        out = cexec("tar jcvf %(targz)s %(basename)s" % locals())
    finally:
        old.chdir()
    assert targz.check(file=1)
    assert targz.size() > 0
    return targz 

def makezip(target):
    tzip = target + ".zip" 
    if tzip.check(file=1):
        log("removing", tzip)
        tzip.remove()
    basename = target.basename 
    old = target.dirpath().chdir() 
    try:
        out = cexec("zip -r9 %(tzip)s %(basename)s" % locals())
    finally:
        old.chdir()
    assert tzip.check(file=1)
    assert tzip.size() > 0
    return tzip 

def copydownload(fn): 
    log("copying to download location")
    #fn.copy(dtarget) 
    ddir = DDIR
    out = cexec("cp %(fn)s %(ddir)s" 
                % locals())

def forced_export(BASEURL, target, lineend="LF"): 
    if target.check(dir=1):
        log("removing", target)
        target.remove()
    out = cexec("svn export --native-eol %s %s %s" 
                            %(lineend, BASEURL, target))
    assert target.check(dir=1)

def build_html(target):
    docdir = target.join('pypy').join('doc')
    old = docdir.chdir()
    try:
        # Generate the html files.
        cmd = "python2.4 ../test_all.py -k -test_play1_snippets"
        logexec(cmd)
        r = os.system(cmd)
        if r:
            raise SystemExit, -1
        # Remove any .pyc files created in the process
        target.chdir()
        out = cexec("find . -name '*.pyc' -print0 | xargs -0 -r rm")
    finally:
        old.chdir()

if __name__ == '__main__':
    argc = len(py.std.sys.argv)
    if argc <= 1:
        usage()

    j = 1
    if py.std.sys.argv[1] == '-tag':
        micro = py.std.sys.argv[2]
        assert micro.startswith('.')
        NEWURL = BASEURL.replace('.x', micro)
        r = os.system("svn cp %s %s" % (BASEURL, NEWURL))
        if r:
            raise SystemExit, -1
        BASEURL = NEWURL
        j = 3
        
    ver = py.std.sys.argv[j]
    assert ver.startswith('pypy-')
    tmpdir = py.path.local("/tmp/pypy-release")

    target = tmpdir.join(ver)

    forced_export(BASEURL, target, lineend="LF")
    build_html(target)
    target_targz = maketargz(target)
    assert target_targz.check(file=1) 
    copydownload(target_targz)

    target_tarbzip = maketarbzip(target)
    assert target_tarbzip.check(file=1) 
    copydownload(target_tarbzip)

    forced_export(BASEURL, target, lineend="CRLF")
    build_html(target)
    target_zip = makezip(target)
    assert target_zip.check(file=1) 
    copydownload(target_zip)
