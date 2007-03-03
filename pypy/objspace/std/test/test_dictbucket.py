from pypy.objspace.std.dictbucket import BucketDictImplementation
from pypy.objspace.std.test import test_dictmultiobject


Base = test_dictmultiobject.TestRDictImplementation

class TestBucketDictImplementation(Base):
    ImplementionClass = BucketDictImplementation
    DevolvedClass     = BucketDictImplementation
    DefaultDictImpl   = BucketDictImplementation
