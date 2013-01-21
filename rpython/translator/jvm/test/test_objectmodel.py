import py
from rpython.translator.jvm.test.runtest import JvmTest
from rpython.translator.oosupport.test_template.objectmodel import \
     BaseTestObjectModel

class TestJvmObjectModel(JvmTest, BaseTestObjectModel):
    pass
