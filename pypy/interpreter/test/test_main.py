import unittest
import support

from pypy.interpreter.baseobjspace import OperationError

testcode = """\
def main():
    aStr = 'hello world'
    print len(aStr)

main()
"""

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
        self.assertRaises(OperationError,
                          main.run_file,
                          testfn)

    def test_run_string(self):
        from pypy.interpreter import main
        self.assertRaises(OperationError,
                          main.run_string,
                          testcode,
                          testfn)

if __name__ == '__main__':
    unittest.main()
        
