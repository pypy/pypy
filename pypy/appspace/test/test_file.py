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

    def test_case_readonly(self):
        f=_file.file_('/tmp/tt', 'w')
        self.assertEquals(f.name, '/tmp/tt')
        self.assertEquals(f.mode, 'w')
        self.assertEquals(f.closed, False)
        self.assertEquals(f.encoding, None) # Fix when we find out what this is
        self.assertRaises(TypeError, setattr, f, 'name', 42)
        
def test_main():
    unittest.main()

if __name__ == "__main__":
    test_main()
