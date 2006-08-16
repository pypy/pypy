import autopath
from pypy.objspace.std.dictmultiobject import \
     W_DictMultiObject, setitem__DictMulti_ANY_ANY, getitem__DictMulti_ANY, \
     EmptyDictImplementation
from pypy.conftest import gettestobjspace
from pypy.objspace.std.test import test_dictobject

class TestW_DictObject(test_dictobject.TestW_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withmultidict": True})

class AppTest_DictObject(test_dictobject.AppTest_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withmultidict": True})

class TestDictImplementation:
    def setup_method(self,method):
        self.space = test_dictobject.FakeSpace()
        self.space.emptydictimpl = EmptyDictImplementation(self.space)
        self.space.DictObjectCls = W_DictMultiObject

    def test_stressdict(self):
        from random import randint
        d = self.space.DictObjectCls(self.space)
        N = 10000
        pydict = {}
        for i in range(N):
            x = randint(-N, N)
            setitem__DictMulti_ANY_ANY(self.space, d, x, i)
            pydict[x] = i
        for x in pydict:
            assert pydict[x] == getitem__DictMulti_ANY(self.space, d, x)
