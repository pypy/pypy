import unittest
import testsupport
from cStringIO import StringIO

from pypy.interpreter.baseobjspace import OperationError

testcode = """\
def main():
    aStr = 'hello world'
    print len(aStr)

main()
"""

testresultoutput = '11\n'

capture = StringIO()

def checkoutput(expected_output,f,*args):
    space = testsupport.objspace()
    w_sys = space.get_builtin_module(space.wrap("sys"))
    w_oldout = space.getattr(w_sys, space.wrap("stdout"))
    capture.reset()
    space.setattr(w_sys, space.wrap("stdout"), space.wrap(capture))
    try:
        f(*(args + (space,)))
    finally:
        space.setattr(w_sys, space.wrap("stdout"), w_oldout)

    return capture.getvalue() == expected_output

testfn = 'tmp_hello_world.py'

class TestMain(unittest.TestCase):

    def setUp(self):
        ofile = open(testfn, 'w')
        ofile.write(testcode)
        ofile.close()

    def tearDown(self):
        import os
        os.remove(testfn)

    def test_run_file(self):
        from pypy.interpreter import main
        self.assert_(checkoutput(testresultoutput,main.run_file,testfn))

    def test_run_string(self):
        from pypy.interpreter import main
        self.assert_(checkoutput(testresultoutput,
                                 main.run_string,testcode,testfn))

if __name__ == '__main__':
    unittest.main()
        
