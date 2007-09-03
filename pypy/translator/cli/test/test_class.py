import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.oosupport.test_template.class_ import BaseTestClass, BaseTestSpecialcase

class TestCliClass(CliTest, BaseTestClass):    
    pass

class TestCliSpecialCase(CliTest, BaseTestSpecialcase):
    pass
