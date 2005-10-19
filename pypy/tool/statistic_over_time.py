import py
from py.__.misc.cmdline.countloc import get_loccount
import datetime
import time

try: 
    path = py.path.svnwc(py.std.sys.argv[1])
except IndexError: 
    path = py.path.svnwc()

tempdir = py.path.svnwc(py.test.ensuretemp("pypy-dist"))
print "checking out"
tempdir.checkout("http://codespeak.net/svn/pypy/dist")
print "done"
pypy = tempdir.join('pypy')

class DailyStatistic(object):
    pass

statistic = []

curr_rev = tempdir.info().rev

while curr_rev > 1:
    num_revs = 0
    num_files = 0
    num_testfiles = 0
    num_lines = 0
    num_testlines = 0
    curr_rev = tempdir.info(usecache=0).rev
    olddate = datetime.date(*time.gmtime(pypy.info(0).mtime)[:3])
    date = olddate
    while date == olddate:
        counter, nf, nl, ntf, ntl = get_loccount([pypy.localpath])
        num_revs += 1
        num_files = max(num_files, nf)
        num_testfiles = max(num_testfiles, ntf)
        num_lines = max(num_lines, nl)
        num_testlines = max(num_testlines, ntl)
        olddate = date
        tempdir.update(rev=curr_rev - 2)
        curr_rev = tempdir.info(usecache=0).rev
        date = datetime.date(*time.gmtime(pypy.info(0).mtime)[:3])
    print date, num_revs, num_files, num_testfiles, num_lines, num_testlines
