#! /usr/bin/env python
import autopath
import py
import sys
        
mydir = py.path.local(__file__).dirpath().realpath()
from pypy.tool.pytest import htmlreport 
from pypy.tool.pytest import confpath 

if __name__ == '__main__':
    if len(sys.argv) > 1:
        testresultdir = py.path.local(sys.argv[1])
        assert testresultdir.check(dir=1)        
    else:
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
    rep = htmlreport.HtmlReport(testresultdir)
    rep.parselatest()

    print "making html files"
    rep.makeindex(testresultdir.join('index.html'))
