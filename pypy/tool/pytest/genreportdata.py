import autopath
import py
mydir = py.magic.autopath().dirpath().realpath()
from pypy.tool.pytest import htmlreport 
from pypy.tool.pytest import confpath 

if __name__ == '__main__': 
    testresultdir = confpath.testresultdir 
    assert testresultdir.check(dir=1)

    resultwc = py.path.svnwc(testresultdir)

    print "updating", resultwc
    resultwc.update()

    print "traversing", mydir 
    rep = htmlreport.HtmlReport()
    rep.parse_all(testresultdir)

    print "making html files"
    rep.makeindex(testresultdir.join('index.html'))
