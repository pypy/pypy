import py
from py.impl.misc.cmdline.countloc import get_loccount
import datetime
import time

URL = "http://codespeak.net/svn/pypy/dist"

tempdir = py.path.svnwc(py.test.ensuretemp("pypy-dist"))
print "checking out"
tempdir.checkout(URL)
print "done"
pypy = tempdir.join('pypy')

statistic = []

curr_rev = tempdir.info().rev

try:
    while curr_rev > 7024: #afterwards the behaviour becomes strange :-(
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
            except Exception, e:
                print e
                tempdir.localpath.remove(1)
                tempdir.localpath.mkdir()
                while 1:
                    try:
                        tempdir._svn("co -r %r" % (curr_rev - 1), URL)
                    except KeyboardInterrupt:
                        raise
                    except Exception, e:
                        print e, curr_rev
                        curr_rev -= 1
                    else:
                        break
            info = tempdir.info(usecache=0)
            curr_rev = info.rev
            date = datetime.date(*time.gmtime(info.mtime)[:3])
        counter, num_files, num_lines, num_testfiles, num_testlines = get_loccount([pypy.localpath])
        print
        print date, num_revs, num_files, num_testfiles, num_lines, num_testlines
        statistic.append([date, num_revs, num_files, num_testfiles, num_lines, num_testlines])
        f = file("intermediate.txt", "a")
        print >> f, date, num_revs, num_files, num_testfiles, num_lines, num_testlines
        f.close()
finally:
    import pickle
    f = file("out.txt", "w")
    pickle.dump(statistic, f)
    f.close()
