import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rlib.test.test_objectmodel import BaseTestObjectModel

from pypy.rlib.objectmodel import cast_object_to_weakgcaddress,\
     cast_weakgcaddress_to_object

class TestJvmObjectModel(JvmTest, BaseTestObjectModel):
    pass
