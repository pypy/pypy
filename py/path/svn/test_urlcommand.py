import sys, os
import py
from py.__impl__.path.svn.svntestbase import CommonCommandAndBindingTests 
from py.__impl__.path.svn.test_wccommand import getrepowc 

class TestSvnCommandPath(CommonCommandAndBindingTests):
    def __init__(self):
        repo, wc = getrepowc() 
        self.root = py.path.svnurl(repo)

    def xtest_copy_file(self):
        raise py.test.run.Skipped(msg="XXX fix svnurl first")

    def xtest_copy_dir(self):
        raise py.test.run.Skipped(msg="XXX fix svnurl first")

    def XXXtest_info_log(self):
        url = self.root.join("samplefile")
        res = url.log(rev_start=1155, rev_end=1155, verbose=True)
        assert res[0].revision == 1155 and res[0].author == "jum"
        from time import gmtime
        t = gmtime(res[0].date)
        assert t.tm_year == 2003 and t.tm_mon == 7 and t.tm_mday == 17
