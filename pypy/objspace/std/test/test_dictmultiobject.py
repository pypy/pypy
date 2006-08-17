import autopath
from pypy.objspace.std.dictmultiobject import \
     W_DictMultiObject, setitem__DictMulti_ANY_ANY, getitem__DictMulti_ANY, \
     EmptyDictImplementation, RDictImplementation, StrDictImplementation, \
     SmallDictImplementation, SmallStrDictImplementation, MeasuringDictImplementation
from pypy.conftest import gettestobjspace
from pypy.objspace.std.test import test_dictobject

class TestW_DictObject(test_dictobject.TestW_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withmultidict": True})

class AppTest_DictObject(test_dictobject.AppTest_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withmultidict": True})

class FakeSpace(test_dictobject.FakeSpace):
    def str_w(self, string):
        assert isinstance(string, str)
        return string

    def wrap(self, obj):
        return obj

    def isinstance(self, obj, klass):
        return isinstance(obj, klass)

class TestDictImplementation:
    def setup_method(self,method):
        self.space = FakeSpace()
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

class TestRDictImplementation:
    ImplementionClass = RDictImplementation
    DevolvedClass = RDictImplementation
    EmptyClass = EmptyDictImplementation

    def setup_method(self,method):
        self.space = FakeSpace()
        self.space.DictObjectCls = W_DictMultiObject
        self.space.emptydictimpl = EmptyDictImplementation(self.space)
        self.string = self.space.str_w("fish")
        self.string2 = self.space.str_w("fish2")
        self.impl = self.get_impl()

    def get_impl(self):
        "Needs to be empty, or one entry with key self.string"
        return self.ImplementionClass(self.space)

    def test_setitem(self):
        assert self.impl.setitem(self.string, 1000) is self.impl
        assert self.impl.length() == 1
        assert self.impl.get(self.string) == 1000

    def test_setitem_str(self):
        assert self.impl.setitem_str(self.string, 1000) is self.impl
        assert self.impl.length() == 1
        assert self.impl.get(self.string) == 1000

    def test_delitem(self):
        self.impl.setitem(self.string, 1000)
        self.impl.setitem(self.string2, 2000)
        assert self.impl.length() == 2
        newimpl =  self.impl.delitem(self.string)
        assert self.impl.length() == 1
        assert newimpl is self.impl
        newimpl = self.impl.delitem(self.string2)
        assert self.impl.length() == 0
        assert isinstance(newimpl, self.EmptyClass)

    def test_keys(self):
        self.impl.setitem(self.string, 1000)
        self.impl.setitem(self.string2, 2000)
        keys = self.impl.keys()
        keys.sort()
        assert keys == [self.string, self.string2]

    def test_values(self):
        self.impl.setitem(self.string, 1000)
        self.impl.setitem(self.string2, 2000)
        values = self.impl.values()
        values.sort()
        assert values == [1000, 2000]

    def test_items(self):
        self.impl.setitem(self.string, 1000)
        self.impl.setitem(self.string2, 2000)
        items = self.impl.items()
        items.sort()
        assert items == zip([self.string, self.string2], [1000, 2000])

    def test_iterkeys(self):
        self.impl.setitem(self.string, 1000)
        self.impl.setitem(self.string2, 2000)
        keys = list(self.impl.iterkeys())
        keys.sort()
        assert keys == [self.string, self.string2]

    def test_itervalues(self):
        self.impl.setitem(self.string, 1000)
        self.impl.setitem(self.string2, 2000)
        values = list(self.impl.itervalues())
        values.sort()
        assert values == [1000, 2000]

    def test_iteritems(self):
        self.impl.setitem(self.string, 1000)
        self.impl.setitem(self.string2, 2000)
        items = list(self.impl.iteritems())
        items.sort()
        assert items == zip([self.string, self.string2], [1000, 2000])

    def test_devolve(self):
        impl = self.impl
        for x in xrange(100):
            impl = impl.setitem(self.space.str_w(str(x)), x)
            impl = impl.setitem(x, x)
        assert isinstance(impl, self.DevolvedClass)

class TestStrDictImplementation(TestRDictImplementation):
    ImplementionClass = StrDictImplementation

    def get_impl(self):
        return self.ImplementionClass(self.space, self.string, self.string2)

class TestSmallDictImplementation(TestRDictImplementation):
    ImplementionClass = SmallDictImplementation

    def get_impl(self):
        return self.ImplementionClass(self.space, self.string, self.string2)

class TestMeasuringDictImplementation(TestRDictImplementation):
    ImplementionClass = MeasuringDictImplementation
    DevolvedClass = MeasuringDictImplementation
    EmptyClass = MeasuringDictImplementation

class TestSmallStrDictImplementation(TestRDictImplementation):
    ImplementionClass = SmallStrDictImplementation

    def get_impl(self):
        return self.ImplementionClass(self.space, self.string, self.string2)
