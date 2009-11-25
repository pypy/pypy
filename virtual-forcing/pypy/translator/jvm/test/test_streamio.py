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
    pass

