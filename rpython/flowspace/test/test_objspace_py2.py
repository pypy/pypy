"""In which we test that various pieces of py2-only syntax are supported."""
from __future__ import with_statement
import py

from rpython.flowspace.flowcontext import FlowingError
from .test_objspace import Base


class TestFlowObjSpacePy2(Base):

    #__________________________________________________________
    def raise2(msg):
        raise IndexError, msg

    def test_raise2(self):
        x = self.codetest(self.raise2)
        # XXX can't check the shape of the graph, too complicated...

   #__________________________________________________________
    def raisez(z, tb):
        raise z.__class__,z, tb

    def test_raisez(self):
        x = self.codetest(self.raisez)

    #__________________________________________________________
    def print_(i):
        print i

    def test_print(self):
        x = self.codetest(self.print_)

    def test_bad_print(self):
        def f(x):
            print >> x, "Hello"
        with py.test.raises(FlowingError):
            self.codetest(f)
