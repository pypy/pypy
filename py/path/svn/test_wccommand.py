import py
from py.__impl__.path.svn.svntestbase import CommonSvnTests
from py.__impl__.path.test.fscommon import setuptestfs 

# make a wc directory out of a given root url
# cache previously obtained wcs!
#
def getrepowc():
    repo = py.test.config.tmpdir / 'path' / 'repo'
    wcdir = py.test.config.tmpdir / 'path' / 'wc'
    if not repo.check():
        assert not wcdir.check()
        repo.ensure(dir=1)
        try:
            py.process.cmdexec('svnadmin create %s' % repo)
        except py.process.cmdexec.Error: 
            repo.remove()
            raise py.test.run.Skipped(msg='could not create temporary svn test repository')
        wcdir.ensure(dir=1)
        print "created svn repository", repo
        wc = py.path.svnwc(wcdir) 
        wc.checkout(url='file://%s' % repo) 
        print "checked out new repo into", wc
        setuptestfs(wc)
        wc.join('samplefile').propset('svn:eol-style', 'native')
        wc.commit("testrepo setup rev 1")
        wc.ensure('anotherfile').write('hello')
        wc.commit('second rev') 
        wc.join('anotherfile').write('world')
        wc.commit('third rev') 
    else:
        print "using repository at %s" % repo
        wc = py.path.svnwc(wcdir)
    return ("file://%s" % repo, wc)

class TestWCSvnCommandPath(CommonSvnTests): 
    def __init__(self):
        repo, self.root = getrepowc()

    def test_status_attributes_simple(self):
        def assert_nochange(p):
            s = p.status()
            assert not s.modified
            assert not s.prop_modified
            assert not s.added
            assert not s.deleted

        dpath = self.root.join('sampledir')
        assert_nochange(self.root.join('sampledir'))
        assert_nochange(self.root.join('samplefile'))

    def test_status_added(self):
        nf = self.root.join('newfile')
        nf.write('hello')
        nf.add()
        try:
            s = nf.status()
            assert s.added
            assert not s.modified
            assert not s.prop_modified
        finally:
            nf.revert()

    def test_status_change(self):
        nf = self.root.join('samplefile')
        try:
            nf.write(nf.read() + 'change')
            s = nf.status()
            assert not s.added
            assert s.modified
            assert not s.prop_modified
        finally:
            nf.revert()

    def test_status_added_ondirectory(self):
        sampledir = self.root.join('sampledir')
        try:
            t2 = sampledir.mkdir('t2')
            t1 = t2.join('t1')
            t1.write('test')
            t1.add()
            s = sampledir.status(rec=1)
            assert t1 in s.added
            assert t2 in s.added
        finally:
            t2.revert(rec=1)
            t2.localpath.remove(rec=1)

    def test_status_unknown(self):
        t1 = self.root.join('un1')
        try:
            t1.write('test')
            s = self.root.status()
            assert t1 in s.unknown
        finally:
            t1.localpath.remove()

    def test_status_unchanged(self):
        r = self.root
        s = self.root.status(rec=1)
        assert r.join('samplefile') in s.unchanged
        assert r.join('sampledir') in s.unchanged
        assert r.join('sampledir/otherfile') in s.unchanged

    def test_status_update(self):
        r = self.root
        try:
            r.update(rev=1)
            s = r.status(updates=1, rec=1)
            assert r.join('anotherfile') in s.update_available
            assert len(s.update_available) == 1
        finally:
            r.update()

    def test_diff(self):
        p = self.root / 'anotherfile'
        out = p.diff(rev=2)
        assert out.find('hello') != -1 

    def test_join_abs(self):
        s = str(self.root.localpath)
        n = self.root.join(s, abs=1)
        assert self.root == n

    def test_join_abs2(self):
        assert self.root.join('samplefile', abs=1) == self.root.join('samplefile')

    def test_str_gives_localpath(self):
        assert str(self.root) == str(self.root.localpath) 

    def test_versioned(self):
        assert self.root.check(versioned=1)
        assert self.root.join('samplefile').check(versioned=1)
        assert not self.root.join('notexisting').check(versioned=1)
        notexisting = self.root.join('hello').localpath
        try:
            notexisting.write("")
            assert self.root.join('hello').check(versioned=0)
        finally:
            notexisting.remove()

    def test_properties(self):
        try:
            self.root.propset('gaga', 'this')
            assert self.root.propget('gaga') == 'this'
            assert self.root in self.root.status().prop_modified
            assert 'gaga' in self.root.proplist()
            assert self.root.proplist()['gaga'] == 'this'

        finally:
            self.root.propdel('gaga')

    def test_proplist_recursive(self):
        s = self.root.join('samplefile') 
        s.propset('gugu', 'that') 
        try:
            p = self.root.proplist(rec=1) 
            assert self.root / 'samplefile' in p 
        finally:
            s.propdel('gugu')

    def test_long_properties(self):
        value = """
        vadm:posix : root root 0100755
        Properties on 'chroot/dns/var/bind/db.net.xots':
                """
        try:
            self.root.propset('gaga', value)
            backvalue = self.root.propget('gaga') 
            assert backvalue == value
            #assert len(backvalue.split('\n')) == 1
        finally:
            self.root.propdel('gaga')


    def test_ensure(self):
        newpath = self.root.ensure('a', 'b', 'c')
        try:
            assert newpath.check(exists=1, versioned=1)
        finally:
            self.root.join('a').remove(force=1)

    def test_not_versioned(self):
        p = self.root.localpath.mkdir('whatever') 
        f = self.root.localpath.ensure('testcreatedfile') 
        try:
            assert self.root.join('whatever').check(versioned=0)
            assert self.root.join('testcreatedfile').check(versioned=0)
            assert not self.root.join('testcreatedfile').check(versioned=1)
        finally:
            p.remove(rec=1)
            f.remove()

    #def test_log(self):
    #   l = self.root.log()
    #   assert len(l) == 3  # might need to be upped if more tests are added

class XTestWCSvnCommandPathSpecial:

    rooturl = 'http://codespeak.net/svn/py.path/trunk/dist/py.path/test/data'
    #def test_update_none_rev(self):
    #    path = tmpdir.join('checkouttest')
    #    wcpath = newpath(xsvnwc=str(path), url=self.rooturl)
    #    try:
    #        wcpath.checkout(rev=2100)
    #        wcpath.update()
    #        assert wcpath.info().rev > 2100
    #    finally:
    #        wcpath.localpath.remove(rec=1)
