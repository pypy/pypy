import py
import sys
from py.__impl__.path.test.fscommon import setuptestfs
checker = py.path.checker 
local = py.path.local 

class TestPOSIXLocalPath:
    #root = local(TestLocalPath.root)
    disabled = sys.platform == 'win32'

    def setup_class(cls):
        cls.root = py.test.config.tmpdir / 'TestPosixLocalPath' 
        cls.root.ensure(dir=1)
        setuptestfs(cls.root)

    def test_hardlink(self):
        tmpdir = local(local.mkdtemp())
        try:
            linkpath = tmpdir.join('test')
            filepath = tmpdir.join('file')
            filepath.write("Hello")
            linkpath.mklinkto(filepath)
            assert filepath.read() == linkpath.read()
        finally:
            tmpdir.remove(rec=1)

    def test_symlink_are_identical(self):
        tmpdir = local(local.mkdtemp())
        try:
            filepath = tmpdir.join('file')
            filepath.write("Hello")
            linkpath = tmpdir.join('test')
            linkpath.mksymlinkto(filepath)
            assert filepath.read() == linkpath.read()
        finally:
            tmpdir.remove(rec=1)

    def test_symlink_isfile(self):
        tmpdir = local(local.mkdtemp())
        try:
            linkpath = tmpdir.join('test')
            filepath = tmpdir.join('file')
            filepath.write("")
            linkpath.mksymlinkto(filepath)
            assert linkpath.check(file=1)
            assert not linkpath.check(link=0, file=1)
        finally:
            tmpdir.remove(rec=1)

    def test_symlink_relative(self):
        tmpdir = local(local.mkdtemp())
        try:
            linkpath = tmpdir.join('test')
            filepath = tmpdir.join('file')
            filepath.write("Hello")
            linkpath.mksymlinkto(filepath, absolute=False)
            assert linkpath.readlink() == "file"
            assert filepath.read() == linkpath.read()
        finally:
            tmpdir.remove(rec=1)

    def test_visit_recursive_symlink(self):
        tmpdir = local.mkdtemp()
        try:
            linkpath = tmpdir.join('test')
            linkpath.mksymlinkto(tmpdir)
            visitor = tmpdir.visit(None, checker(link=0))
            assert list(visitor) == [linkpath]
            #check.equal(list(tmpdir.visit()), [linkpath])
        finally:
            tmpdir.remove(rec=1)

    def test_symlink_isdir(self):
        tmpdir = local.mkdtemp()
        try:
            linkpath = tmpdir.join('test')
            linkpath.mksymlinkto(tmpdir)
            assert linkpath.check(dir=1)
            assert not linkpath.check(link=0, dir=1)
        finally:
            tmpdir.remove(rec=1)

    def test_symlink_remove(self):
        tmpdir = local.mkdtemp()
        try:
            linkpath = tmpdir.join('test')
            linkpath.mksymlinkto(linkpath) # point to itself 
            assert linkpath.check(dir=0) 
            assert linkpath.check(link=1)
            linkpath.remove()
            assert not linkpath.check() 
        finally:
            tmpdir.remove(rec=1)

    def test_realpath_file(self):
        tmpdir = local.mkdtemp()
        try:
            linkpath = tmpdir.join('test')
            filepath = tmpdir.join('file')
            filepath.write("")
            linkpath.mksymlinkto(filepath)
            realpath = linkpath.realpath()
            assert realpath.get('basename') == 'file'
        finally:
            tmpdir.remove(rec=1)

    def test_owner(self):
        from pwd import getpwuid
        assert getpwuid(self.root.stat().st_uid)[0] == self.root.owner()

    def test_group(self):
        from grp import getgrgid
        assert getgrgid(self.root.stat().st_gid)[0] == self.root.group()

    def XXXtest_atime(self):
        # XXX disabled. this test is just not platform independent enough
        #     because acesstime resolution is very different through
        #     filesystems even on one platform. 
        import time
        path = self.root.join('samplefile')
        atime = path.atime()
        time.sleep(1)
        path.read(1)
        assert path.atime() != atime

    def testcommondir(self):
        # XXX This is here in local until we find a way to implement this
        #     using the subversion command line api.
        p1 = self.root.join('something')
        p2 = self.root.join('otherthing')
        assert p1.commondir(p2) == self.root
        assert p2.commondir(p1) == self.root

    def testcommondir_nocommon(self):
        # XXX This is here in local until we find a way to implement this
        #     using the subversion command line api.
        p1 = self.root.join('something')
        p2 = local(os.sep+'blabla')
        assert p1.commondir(p2) is None


    def test_chmod_simple_int(self):
        print "self.root is", self.root
        mode = self.root.mode()
        self.root.chmod(mode/2) 
        try:
            assert self.root.mode() != mode
        finally:
            self.root.chmod(mode)
            assert self.root.mode() == mode 

    def test_chmod_rec_int(self):
        # XXX fragile test
        print "self.root is", self.root
        recfilter = checker(dotfile=0)
        oldmodes = {}
        for x in self.root.visit(rec=recfilter):
            oldmodes[x] = x.mode()
        self.root.chmod(0772, rec=1)
        try:
            for x in self.root.visit(rec=recfilter):
                assert x.mode() & 0777 == 0772 
        finally:
            for x,y in oldmodes.items():
                x.chmod(y) 

    def test_chown_identity(self):
        owner = self.root.owner()
        group = self.root.group()
        self.root.chown(owner, group) 

    def test_chown_identity_rec_mayfail(self):
        owner = self.root.owner()
        group = self.root.group()
        self.root.chown(owner, group) 
