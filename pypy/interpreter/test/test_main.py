import unittest
import autopath
from cStringIO import StringIO
from pypy.tool.udir import udir

from pypy.tool import testit
from pypy.interpreter.baseobjspace import OperationError

from pypy.interpreter import main

testcode = """\
def main():
    aStr = 'hello world'
    print len(aStr)

main()
"""

testresultoutput = '11\n'


def checkoutput(expected_output,f,*args):
    space = testit.objspace()
    w_sys = space.get_builtin_module("sys")
    w_oldout = space.getattr(w_sys, space.wrap("stdout"))
    capturefn = udir.join('capturefile')
    capturefile = capturefn.open('w') 
    space.setattr(w_sys, space.wrap("stdout"), space.wrap(capturefile))
    try:
        f(*(args + (space,)))
    finally:
        space.setattr(w_sys, space.wrap("stdout"), w_oldout)
    capturefile.close() 
    return capturefn.read() == expected_output

testfn = 'tmp_hello_world.py'

class TestMain(testit.TestCase):

    def setUp(self):
        self.space = testit.objspace()
        ofile = open(testfn, 'w')
        ofile.write(testcode)
        ofile.close()

    def tearDown(self):
        import os
        os.remove(testfn)

    def test_run_file(self):
        self.assert_(checkoutput(testresultoutput,main.run_file,testfn))

    def test_run_string(self):
        self.assert_(checkoutput(testresultoutput,
                                 main.run_string,testcode,testfn))

    def test_eval_string(self):
        w_x = main.eval_string('2+2', space=self.space)
        self.assertEqual_w(w_x, self.space.wrap(4))

if __name__ == '__main__':
    testit.main()
