import py
from py.__.misc.cmdline.countloc import get_loccount
import datetime
import time

try: 
    path = py.path.svnwc(py.std.sys.argv[1])
except IndexError: 
    path = py.path.svnwc()

URL = "http://codespeak.net/svn/pypy/dist"

tempdir = py.path.svnwc(py.test.ensuretemp("pypy-dist"))
print "checking out"
tempdir.checkout(URL)
print "done"
pypy = tempdir.join('pypy')

class DailyStatistic(object):
    pass

statistic = []

curr_rev = tempdir.info().rev

try:
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
            try:
                tempdir.update(rev=curr_rev - 1)
            except:
                tempdir.localpath.remove(1)
                tempdir.localpath.mkdir()
                tempdir.checkout(URL, rev=curr_rev - 1)
            curr_rev = tempdir.info(usecache=0).rev
            date = datetime.date(*time.gmtime(pypy.info(0).mtime)[:3])
        print date, num_revs, num_files, num_testfiles, num_lines, num_testlines
        statistic.append([date, num_revs, num_files, num_testfiles, num_lines, num_testlines])
finally:
    import pickle
    f = file("out.txt", "w")
    pickle.dump(statistic, f)
    f.close()
