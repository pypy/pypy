from py import path, test
from py.__impl__.path.svn.test_wccommand import getrepowc 

class TestAPI:
    def __init__(self):
        self.root = test.config.tmpdir.ensure('local', dir=1)

    def repr_eval_test(self, p):
        r = repr(p)
        from py.path import local,svnurl, svnwc, extpy
        y = eval(r)
        assert y == p 

    def test_defaultlocal(self):
        p = path.local()
        assert hasattr(p, 'atime')
        assert hasattr(p, 'group')
        assert hasattr(p, 'setmtime')
        assert p.check()
        assert p.check(local=1)
        assert p.check(svnwc=0)
        assert not p.check(svnwc=1)
        self.repr_eval_test(p)

        #assert p.std.path()

    def test_local(self):
        p = path.local()
        assert hasattr(p, 'atime')
        assert hasattr(p, 'setmtime')
        assert p.check()
        assert p.check(local=1)
        self.repr_eval_test(p)

    def test_svnurl(self):
        p = path.svnurl('http://codespeak.net/svn/py')
        assert p.check(svnurl=1)
        self.repr_eval_test(p)

    def test_svnwc(self):
        p = path.svnwc(self.root) 
        assert p.check(svnwc=1)
        self.repr_eval_test(p)

    #def test_fspy(self):
    #    p = path.py('smtplib.SMTP') 
    #    self.repr_eval_test(p)


if __name__ == '__main__':
    test.main()

