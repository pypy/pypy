
import os, sys
import autopath 
import py
from pypy.documentation.revreport import delta 
from pypy.tool.pypyrev import pypyrev 
from py.__.test.tool.outerrcapture import SimpleOutErrCapture 

BASE = py.path.local(delta.__file__).dirpath() 
DEST = BASE.join('revdata') 

assert DEST.dirpath().check() 

def updatecurrent(revdir):
    l = []
    for x in DEST.listdir(): 
        try: 
            x = int(x.basename)
        except (TypeError, ValueError): 
            pass
        else: 
            l.append(x) 
    latest = DEST.join(str(max(l)))
    if latest != revdir:   # another process is busy generating the next rev
        return             # then don't change the link!
    assert latest.check()
    current = DEST.join('current') 
    if current.check(): 
        current.remove() 
    if sys.platform == 'win32': 
        latest.copy(current) 
    else: 
        current.mksymlinkto(latest) 

if __name__ == '__main__':
    rev = pypyrev()  
    revdir = DEST.ensure(str(rev), dir=1) 
    BASE.join('delta.css').copy(revdir) 
    BASE.join('delta.js').copy(revdir) 

    if py.std.sys.stdout.isatty(): 
        delta.genreport(revdir) 
    else: 
        capture = SimpleOutErrCapture() 
        try: 
            delta.genreport(revdir) 
        except: 
            out, err = capture.reset()  
            print "stdout", out 
            print "stderr", err 
            raise 
        else: 
            out, err = capture.reset() 
            print "stdout"
            print out 
    print "generated into", revdir 
    updatecurrent(revdir)
