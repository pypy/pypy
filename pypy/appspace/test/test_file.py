import autopath
from pypy.appspace import _file
import unittest

class FileTestCase(unittest.TestCase):
    def setUp(self):
        self.fd = _file.file_('test_file.py', 'r')

    def tearDown(self):
        self.fd.close()
        
    def test_case_1(self):
        self.assertEquals(self.fd.tell(), 0)

def test_main():
    unittest.main()


if __name__ == "__main__":
    test_main()
