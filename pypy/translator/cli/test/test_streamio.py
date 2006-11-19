import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rlib.test.test_streamio import BaseTestBufferingInputStreamTests,\
     BaseTestBufferingOutputStream, BaseTestLineBufferingOutputStream,\
     BaseTestCRLFFilter, BaseTestBufferingInputOutputStreamTests,\
     BaseTestTextInputFilter, BaseTestTextOutputFilter

class TestBufferingInputStreamTests(CliTest, BaseTestBufferingInputStreamTests):
    pass

class TestBufferingOutputStream(CliTest, BaseTestBufferingOutputStream):
    pass

class TestLineBufferingOutputStream(CliTest, BaseTestLineBufferingOutputStream):
    def test_write(self):
        py.test.skip('Fixme!')

class TestCRLFFilter(CliTest, BaseTestCRLFFilter):
    pass

class TestBufferingInputOutputStreamTests(CliTest, BaseTestBufferingInputOutputStreamTests):
    pass

class TestTextInputFilter(CliTest, BaseTestTextInputFilter):
    pass

class TestTextOutputFilter(CliTest, BaseTestTextOutputFilter):
    pass

