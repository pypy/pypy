
from pypy.lang.scheme.interactive import check_parens
import py
import re
import sys

def test_paren():
    assert check_parens("(((  ))())")
    assert not check_parens("(x()x")

class TestInteractive:
    def _spawn(self, *args, **kwds):
        try:
            import pexpect
        except ImportError, e:
            py.test.skip(str(e))
        kwds.setdefault('timeout', 10)
        print 'SPAWN:', args, kwds
        child = pexpect.spawn(*args, **kwds)
        child.logfile = sys.stdout
        return child

    def spawn(self, argv=[]):
        path = py.magic.autopath()/".."/".."/"interactive.py"
        return self._spawn(str(path), argv)

    def test_interactive(self):
        child = self.spawn()
        child.expect("->")
        child.sendline("(+ 1 2)")
        child.expect("3W")

