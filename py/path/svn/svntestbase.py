import py
from py import path, test, process
from py.__impl__.path.test.fscommon import CommonFSTests
from py.__impl__.path.svn import cache 

class CommonSvnTests(CommonFSTests):

    def setup_method(self, meth):
        bn = meth.func_name 
        if bn.startswith('test_remove') or bn.startswith('test_move'):
            raise py.test.run.Skipped(msg=
                "tests for (re)move require better svn state management")

    def test_propget(self):
        url = self.root.join("samplefile")
        value = url.propget('svn:eol-style')
        assert value == 'native'

    def test_proplist(self):
        url = self.root.join("samplefile")
        res = url.proplist()
        assert res['svn:eol-style'] == 'native'

    def test_info(self):
        url = self.root.join("samplefile")
        res = url.info()
        assert res.size > len("samplefile") and res.created_rev >= 0

    def xxxtest_info_log(self):
        url = self.root.join("samplefile")
        res = url.log(rev_start=1155, rev_end=1155, verbose=True)
        assert res[0].revision == 1155 and res[0].author == "jum"
        from time import gmtime
        t = gmtime(res[0].date)
        assert t.tm_year == 2003 and t.tm_mon == 7 and t.tm_mday == 17

class CommonCommandAndBindingTests(CommonSvnTests):
    def test_trailing_slash_is_stripped(self):
        # XXX we need to test more normalizing properties
        url = self.root.join("/")
        assert self.root == url

    #def test_different_revs_compare_unequal(self):
    #    newpath = self.root.new(rev=1199)
    #    assert newpath != self.root

    def test_exists_svn_root(self):
        assert self.root.check()

    #def test_not_exists_rev(self):
    #    url = self.root.__class__(self.rooturl, rev=500)
    #    assert url.check(exists=0)

    #def test_nonexisting_listdir_rev(self):
    #    url = self.root.__class__(self.rooturl, rev=500)
    #    raises(error.FileNotFound, url.listdir)

    #def test_newrev(self):
    #    url = self.root.new(rev=None) 
    #    assert url.rev == None
    #    assert url.strpath == self.root.strpath
    #    url = self.root.new(rev=10)
    #    assert url.rev == 10

    #def test_info_rev(self):
    #    url = self.root.__class__(self.rooturl, rev=1155)
    #    url = url.join("samplefile")
    #    res = url.info()
    #    assert res.size > len("samplefile") and res.created_rev == 1155

    # the following tests are easier if we have a path class 
    def test_repocache_simple(self):
        repocache = cache.RepoCache()
        repocache.put(self.root.strpath, 42) 
        url, rev = repocache.get(self.root.join('test').strpath)
        assert rev == 42 
        assert url == self.root.strpath

    def test_repocache_notimeout(self):
        repocache = cache.RepoCache()
        repocache.timeout = 0
        repocache.put(self.root.strpath, self.root.rev)
        url, rev = repocache.get(self.root.strpath)
        assert rev == -1
        assert url == self.root.strpath

    def test_repocache_outdated(self):
        repocache = cache.RepoCache()
        repocache.put(self.root.strpath, 42, timestamp=0)
        url, rev = repocache.get(self.root.join('test').strpath)
        assert rev == -1
        assert url == self.root.strpath

    def _test_getreporev(self):
        """ this test runs so slow it's usually disabled """
        old = cache.repositories.repos 
        try:
            _repocache.clear()
            root = self.root.new(rev=-1)
            url, rev = cache.repocache.get(root.strpath)
            assert rev>=0
            assert url == svnrepourl
        finally:
            repositories.repos = old

#cache.repositories.put(svnrepourl, 1200, 0)
