import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.objectmodel import \
     BaseTestObjectModel

class TestJvmObjectModel(JvmTest, BaseTestObjectModel):
    pass
