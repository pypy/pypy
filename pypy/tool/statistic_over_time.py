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
            num_revs += 1
            olddate = date
            try:
                tempdir.update(rev=curr_rev - 1)
            except KeyboardInterrupt:
                raise
            except:
                tempdir.localpath.remove(1)
                tempdir.localpath.mkdir()
                while 1:
                    try:
                        tempdir.checkout(URL, rev=curr_rev - 1)
                    except KeyboardInterrupt:
                        raise
                    except:
                        curr_rev -= 1
                    else:
                        break
            info = tempdir.info(usecache=0)
            curr_rev = info.rev
            date = datetime.date(*time.gmtime(info.mtime)[:3])
        counter, num_files, num_lines, num_testfiles, num_testlines = get_loccount([pypy.localpath])
        print date, num_revs, num_files, num_testfiles, num_lines, num_testlines
        statistic.append([date, num_revs, num_files, num_testfiles, num_lines, num_testlines])
finally:
    import pickle
    f = file("out.txt", "w")
    pickle.dump(statistic, f)
    f.close()
