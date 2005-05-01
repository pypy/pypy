import os
import support
_file = support.libmodule("_file")
from pypy.tool.udir import udir 
import py 

class TestFile: 
    def setup_method(self, method):
        self.fd = _file.file(__file__, 'r')

    def teardown_method(self, method):
        self.fd.close()
        
    def test_case_1(self):
        assert self.fd.tell() == 0

    def test_case_readonly(self):
        fn = str(udir.join('temptestfile'))
        f=_file.file(fn, 'w')
        assert f.name == fn
        assert f.mode == 'w'
        assert f.closed == False
        assert f.encoding == None # Fix when we find out what this is
        py.test.raises((TypeError, AttributeError), setattr, f, 'name', 42)

    def test_plain_read(self):
        data1 = self.fd.read()
        data2 = open(__file__, 'r').read()
        assert data1 == data2
