from pypy.interpreter.error import OperationError
from pypy.objspace.std.dictmultiobject import \
     W_DictMultiObject, setitem__DictMulti_ANY_ANY, getitem__DictMulti_ANY, \
     EmptyDictImplementation, RDictImplementation, StrDictImplementation, \
     SmallDictImplementation, SmallStrDictImplementation, MeasuringDictImplementation
from pypy.conftest import gettestobjspace
from pypy.objspace.std.test import test_dictobject

class TestW_DictMultiObject(test_dictobject.TestW_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withmultidict": True})

class AppTest_DictMultiObject(test_dictobject.AppTest_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withmultidict": True})

    def test_len_iter(self):
        d = {1: 2, 3: 4}
        i = iter(d)
        assert len(i) == 2
        x = i.next()
        assert len(i) == 1
        y = i.next()
        assert len(i) == 0
        l = [x, y]
        l.sort()
        assert l == [1, 3]
        raises(StopIteration, i.next)
        raises(StopIteration, i.next)

    def test_emptydict_unhashable(self):
        raises(TypeError, "{}[['x']]")

    def test_string_subclass_via_setattr(self):
        skip("issue383")
        class S(str):
            def __hash__(self):
                return 123
        s = S("abc")
        setattr(s, s, 42)
        assert s.__dict__.keys()[0] is s
        assert getattr(s, s) == 42


class TestW_DictSharing(test_dictobject.TestW_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withsharingdict": True})

class AppTest_DictSharing(test_dictobject.AppTest_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withsharingdict": True})

    def test_values_does_not_share(self):
        class A(object):
            pass
        a = A()
        a.abc = 12
        l = a.__dict__.values()
        assert l == [12]
        l[0] = 24
        assert a.abc == 12

    def test_items(self):
        class A(object):
            pass
        a = A()
        a.abc = 12
        a.__dict__.items() == [("abc", 12)]



class TestW_DictSmall(test_dictobject.TestW_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withsmalldicts": True})

class AppTest_DictSmall(test_dictobject.AppTest_DictObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withsmalldicts": True})


class C: pass

class FakeSpace(test_dictobject.FakeSpace):
    def str_w(self, string):
        assert isinstance(string, str)
        return string

    def wrap(self, obj):
        return obj

    def isinstance(self, obj, klass):
        return isinstance(obj, klass)

    def newtuple(self, l):
        return tuple(l)

    w_StopIteration = StopIteration
    w_None = None
    StringObjectCls = None  # xxx untested: shortcut in StrDictImpl.getitem

class TestDictImplementation:
    def setup_method(self,method):
        self.space = FakeSpace()
        self.space.emptydictimpl = EmptyDictImplementation(self.space)
        self.space.DictObjectCls = W_DictMultiObject
        self.space.DefaultDictImpl = RDictImplementation

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
    DefaultDictImpl = RDictImplementation

    def setup_method(self,method):
        self.space = FakeSpace()
        self.space.DictObjectCls = W_DictMultiObject
        self.space.emptydictimpl = EmptyDictImplementation(self.space)
        self.space.DefaultDictImpl = self.DefaultDictImpl
        self.string = self.space.wrap("fish")
        self.string2 = self.space.wrap("fish2")
        self.impl = self.get_impl()

    def get_impl(self):
        "Needs to be empty, or one entry with key self.string"
        return self.ImplementionClass(self.space)

    def test_setitem(self):
        assert self.impl.setitem(self.string, 1000) is self.impl
        assert self.impl.length() == 1
        assert self.impl.get(self.string) == 1000

    def test_setitem_str(self):
        assert self.impl.setitem_str(self.space.str_w(self.string), 1000) is self.impl
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
        iteratorimplementation = self.impl.iterkeys()
        keys = []
        while 1:
            key = iteratorimplementation.next()
            if key is None:
                break
            keys.append(key)
        keys.sort()
        assert keys == [self.string, self.string2]

    def test_itervalues(self):
        self.impl.setitem(self.string, 1000)
        self.impl.setitem(self.string2, 2000)
        iteratorimplementation = self.impl.itervalues()
        values = []
        while 1:
            value = iteratorimplementation.next()
            if value is None:
                break
            values.append(value)
        values.sort()
        assert values == [1000, 2000]

    def test_iteritems(self):
        self.impl.setitem(self.string, 1000)
        self.impl.setitem(self.string2, 2000)
        iteratorimplementation = self.impl.iteritems()
        items = []
        while 1:
            item = iteratorimplementation.next()
            if item is None:
                break
            items.append(item)
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
