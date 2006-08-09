#! /usr/bin/env python
import autopath
import py
import sys
if sys.version_info[:2] != (2,3):
        raise RuntimeError("Genreportdata.py needs Python 2.3")
        
mydir = py.magic.autopath().dirpath().realpath()
from pypy.tool.pytest import htmlreport 
from pypy.tool.pytest import confpath 

if __name__ == '__main__': 
    testresultdir = confpath.testresultdir 
    assert testresultdir.check(dir=1)
    try:
        resultwc = py.path.svnwc(testresultdir)
        print "updating", resultwc
        resultwc.update()
    except KeyboardInterrupt, RuntimeError:
        raise
    except Exception,e: #py.process.ExecutionFailed,e:
        print >> sys.stderr, "Warning: ",e #Subversion update failed"

    print "traversing", mydir 
    rep = htmlreport.HtmlReport()
    rep.parselatest()

    print "making html files"
    rep.makeindex(testresultdir.join('index.html'))
