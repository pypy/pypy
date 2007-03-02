from pypy.objspace.std.dictstrobject import W_DictStrObject, setitem__DictStr_ANY_ANY, getitem__DictStr_ANY
from pypy.conftest import gettestobjspace
from pypy.objspace.std.test import test_dictobject

class TestW_DictObject(test_dictobject.TestW_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withstrdict": True})

class AppTest_DictObject(test_dictobject.AppTest_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withstrdict": True})

class TestDictImplementation:
    def setup_method(self,method):
        self.space = test_dictobject.FakeSpace()
        self.space.DictObjectCls = W_DictStrObject

    def test_stressdict(self):
        from random import randint
        d = self.space.DictObjectCls(self.space)
        N = 10000
        pydict = {}
        for i in range(N):
            x = randint(-N, N)
            setitem__DictStr_ANY_ANY(self.space, d, x, i)
            pydict[x] = i
        for x in pydict:
            assert pydict[x] == getitem__DictStr_ANY(self.space, d, x)
