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
    import sys
    oldout = sys.stdout
    try:
        capture.reset()
        sys.stdout = capture
        f(*args)
    finally:
        sys.stdout = oldout

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
        
