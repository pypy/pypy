import os
import autopath
from pypy.appspace import _file
from pypy.tool.udir import udir 
import py 
import unittest

class TestFile: 
    def setup_method(self, method):
        filename = os.path.join(autopath.this_dir, 'test_file.py')
        self.fd = _file.file_(filename, 'r')

    def teardown_method(self, method):
        self.fd.close()
        
    def test_case_1(self):
        assert self.fd.tell() == 0

    def test_case_readonly(self):
        fn = str(udir.join('temptestfile'))
        f=_file.file_(fn, 'w')
        assert f.name == fn
        assert f.mode == 'w'
        assert f.closed == False
        assert f.encoding == None # Fix when we find out what this is
        py.test.raises(TypeError, setattr, f, 'name', 42)
