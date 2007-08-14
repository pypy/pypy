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
        child.expect("3")

    def test_multiline(self):
        child = self.spawn()
        child.expect("-> ")
        child.sendline("(+ 1")
        child.expect(".. ")
        child.sendline(" 2)")
        child.expect("3")

    def test_unbound_variable(self):
        child = self.spawn()
        child.expect("-> ")
        child.sendline("x")
        child.expect("Unbound variable x")
        child.expect("-> ")

    def test_syntax_error(self):
        child = self.spawn()
        child.expect("-> ")
        child.sendline(")(")
        child.expect("parse error")
        child.expect("-> ")

    def test_multiline_enter(self):
        child = self.spawn()
        child.expect("-> ")
        child.sendline("")
        child.expect("-> ")
        child.sendline("")
        child.expect("-> ")
        child.sendline("")
        child.expect("-> ")
        child.sendline("")
        # we cannot sendeof, because pexpect is confused :-(
