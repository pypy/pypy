import sys, os
from py.test import main, raises, config 
from py.path import local, checker
from py.__impl__.path.test.fscommon import CommonFSTests, setuptestfs 

class TestLocalPath(CommonFSTests):
    def setup_class(cls):
        cls.root = config.tmpdir / 'TestLocalPath'
        cls.root.ensure(dir=1)
        setuptestfs(cls.root)
        
    def test_initialize_curdir(self):
        assert str(local()) == os.getcwd()

    def test_initialize_reldir(self):
        curdir = os.curdir
        try:
            os.chdir(str(self.root))
            p = local('samplefile')
            assert p.check()
        finally:
            os.chdir(curdir)

    def test_eq_with_strings(self):
        path1 = self.root.join('sampledir')
        path2 = str(path1)
        assert path1 == path2
        assert path2 == path1
        path3 = self.root.join('samplefile')
        assert path3 != path2 
        assert path2 != path3

    def test_dump(self):
        import tempfile
        try:
            fd, name = tempfile.mkstemp()
            f = os.fdopen(fd)
        except AttributeError:
            name = tempfile.mktemp()
            f = open(name, 'w+')
        try:
            d = {'answer' : 42}
            path = local(name)
            path.dumpobj(d)
            from cPickle import load
            dnew = load(f)
            assert d == dnew
        finally:
            f.close()
            os.remove(name)

    def test_setmtime(self):
        import tempfile
        import time
        try:
            fd, name = tempfile.mkstemp()
            os.close(fd)
        except AttributeError:
            name = tempfile.mktemp()
            open(name, 'w').close()
        try:
            mtime = int(time.time())-100
            path = local(name)
            assert path.mtime() != mtime
            path.setmtime(mtime)
            assert path.mtime() == mtime
            path.setmtime()
            assert path.mtime() != mtime
        finally:
            os.remove(name)

    def test_normpath(self):
        new1 = self.root.join("/otherdir")
        new2 = self.root.join("otherdir")
        assert str(new1) == str(new2)

    def test_mkdtemp_creation(self):
        d = local.mkdtemp()
        try:
            assert d.check(dir=1)
        finally:
            d.remove(rec=1)

    def test_tmproot(self):
        d = local.mkdtemp()
        tmproot = local.get_temproot()
        try:
            assert d.check(dir=1)
            assert d.dirpath() == tmproot
        finally:
            d.remove(rec=1)

    def test_ensure_filepath_withdir(self):
        tmpdir = local.mkdtemp()
        try:
            newfile = tmpdir.join('test1','test2')
            newfile.ensure()
            assert newfile.check(file=1)
        finally:
            tmpdir.remove(rec=1)

    def test_ensure_filepath_withoutdir(self):
        tmpdir = local.mkdtemp()
        try:
            newfile = tmpdir.join('test1')
            t = newfile.ensure()
            assert t == newfile
            assert newfile.check(file=1)
        finally:
            tmpdir.remove(rec=1)

    def test_ensure_dirpath(self):
        tmpdir = local.mkdtemp()
        try:
            newfile = tmpdir.join('test1','test2')
            t = newfile.ensure(dir=1)
            assert t == newfile
            assert newfile.check(dir=1)
        finally:
            tmpdir.remove(rec=1)

    def test_mkdir(self):
        tmpdir = local.mkdtemp()
        try:
            new = tmpdir.join('test1')
            new.mkdir()
            assert new.check(dir=1)

            new = tmpdir.mkdir('test2')
            assert new.check(dir=1)
            assert tmpdir.join('test2') == new
        finally:
            tmpdir.remove(rec=1)

    def test_chdir(self):
        import os
        old = local() 
        tmpdir = local.mkdtemp()
        try:
            res = tmpdir.chdir()
            assert str(res) == str(old)
            assert os.getcwd() == str(tmpdir)
        finally:
            old.chdir()
            tmpdir.remove(rec=1)


class TestMisc:
    root = local(TestLocalPath.root)

    def test_make_numbered_dir(self):
        root = local.mkdtemp()
        try:
            for i in range(10):
                numdir = local.make_numbered_dir(root, 'base.', keep=2)
                assert numdir.check()
                assert numdir.get('basename') == 'base.%d' %i
                if i>=1:
                    assert numdir.new(ext=str(i-1)).check()
                if i>=2:
                    assert numdir.new(ext=str(i-2)).check()
                if i>=3:
                    assert not numdir.new(ext=str(i-3)).check()
        finally:
            #print "root was", root
            root.remove(rec=1)

    def test_error_preservation(self):
        raises (OSError, self.root.join('qwoeqiwe').mtime)
        raises (IOError, self.root.join('qwoeqiwe').read)

    #def test_parentdirmatch(self):
    #    local.parentdirmatch('std', startmodule=__name__)

#class XTestLocalPath(TestLocalPath):
#    def __init__(self):
#        TestLocalPath.__init__(self)
#        self.root = local(self.root)
#
#class XXTestLocalPath(TestLocalPath):
#    def __init__(self):
#        TestLocalPath.__init__(self)
#        self.root = local(self.root)

if __name__ == '__main__':
    main()

