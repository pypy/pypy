import os
import autopath
from pypy.appspace import _file
import unittest

class FileTestCase(unittest.TestCase):
    def setUp(self):
        filename = os.path.join(autopath.this_dir, 'test_file.py')
        self.fd = _file.file_(filename, 'r')

    def tearDown(self):
        self.fd.close()
        
    def test_case_1(self):
        self.assertEquals(self.fd.tell(), 0)

def test_main():
    unittest.main()


if __name__ == "__main__":
    test_main()
