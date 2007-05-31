import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rlib.test.test_streamio import BaseTestBufferingInputStreamTests,\
     BaseTestBufferingOutputStream, BaseTestLineBufferingOutputStream,\
     BaseTestCRLFFilter, BaseTestBufferingInputOutputStreamTests,\
     BaseTestTextInputFilter, BaseTestTextOutputFilter

class TestBufferingInputStreamTests(JvmTest, BaseTestBufferingInputStreamTests):
    pass

class TestBufferingOutputStream(JvmTest, BaseTestBufferingOutputStream):
    pass

class TestLineBufferingOutputStream(JvmTest, BaseTestLineBufferingOutputStream):
    pass

class TestCRLFFilter(JvmTest, BaseTestCRLFFilter):
    pass

class TestBufferingInputOutputStreamTests(JvmTest, BaseTestBufferingInputOutputStreamTests):
    pass

class TestTextInputFilter(JvmTest, BaseTestTextInputFilter):
    pass

class TestTextOutputFilter(JvmTest, BaseTestTextOutputFilter):
    def test_write_nl(self):
        py.test.skip("VerifyError - Incompatible object arguments")
        
    def test_write_cr(self):
        py.test.skip("VerifyError - Incompatible object arguments")

    def test_write_crnl(self):
        py.test.skip("VerifyError - Incompatible object arguments")

    def test_write_tell_nl(self):
        py.test.skip("VerifyError - Incompatible object arguments")
    
    def test_write_tell_cr(self):
        py.test.skip("VerifyError - Incompatible object arguments")
    
    def test_write_tell_crnl(self):
        py.test.skip("VerifyError - Incompatible object arguments")
    
    def test_write_seek(self):
        py.test.skip("VerifyError - Incompatible object arguments")
    

