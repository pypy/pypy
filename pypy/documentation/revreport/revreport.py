
import os, sys
import autopath 
import py
from pypy.documentation.revreport import delta 
from pypy.tool.pypyrev import pypyrev 

BASE = py.path.local(delta.__file__).dirpath() 
DEST = BASE.join('revdata') 

assert DEST.dirpath().check() 

if __name__ == '__main__':
    rev = pypyrev()  
    revdir = DEST.ensure(str(rev), dir=1) 
    BASE.join('delta.css').copy(revdir) 
    BASE.join('delta.js').copy(revdir) 
    delta.genreport(revdir) 

    print "generated into", revdir 

    l = []
    for x in DEST.listdir(): 
        try: 
            x = int(x.basename)
        except (TypeError, ValueError): 
            pass
        else: 
            l.append(x) 
    latest = DEST.join(str(max(l)))
    assert latest.check()
    current = DEST.join('current') 
    if current.check(): 
        current.remove() 
    if sys.platform == 'win32': 
        latest.copy(current) 
    else: 
        current.mksymlinkto(latest) 
