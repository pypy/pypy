

import py

log = py.log.Producer("log")
logexec = py.log.Producer("exec")

BASEURL = "file:///svn/pypy/release/0.9.x"
DDIR = py.path.local('/www/codespeak.net/htdocs/download/pypy')

def usage():
    print "usage: %s versionbasename" %(py.std.sys.argv[0])
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

if __name__ == '__main__':
    argc = len(py.std.sys.argv)
    if argc <= 1:
        usage()
    ver = py.std.sys.argv[1] 
    tmpdir = py.path.local("/tmp/pypy-release")

    target = tmpdir.join(ver)

    forced_export(BASEURL, target, lineend="LF")
    target_targz = maketargz(target)
    assert target_targz.check(file=1) 
    copydownload(target_targz)

    target_tarbzip = maketarbzip(target)
    assert target_tarbzip.check(file=1) 
    copydownload(target_tarbzip)

    forced_export(BASEURL, target, lineend="CRLF")
    target_zip = makezip(target)
    assert target_zip.check(file=1) 
    copydownload(target_zip)
