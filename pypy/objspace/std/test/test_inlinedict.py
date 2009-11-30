import py
from pypy.conftest import gettestobjspace
from pypy.objspace.std.inlinedict import make_inlinedict_mixin
from pypy.objspace.std.dictmultiobject import StrDictImplementation
from pypy.objspace.std.test.test_dictmultiobject import FakeSpace
from pypy.objspace.std.test.test_dictmultiobject import BaseTestRDictImplementation
from pypy.objspace.std.sharingdict import SharedDictImplementation

class FakeSubtype:
    nslots = 0

class TestMixin(object):
    Mixin = make_inlinedict_mixin(StrDictImplementation, "content")
    class FakeObject(Mixin):
        def user_setup_slots(self, nslots):
            pass

    fakespace = FakeSpace()

    def make_obj(self):
        obj = self.FakeObject()
        obj.user_setup(self.fakespace, FakeSubtype)
        obj.setdictvalue(self.fakespace, "hello", 1)
        obj.setdictvalue(self.fakespace, "world", 2)
        assert obj._inlined_dict_valid()
        assert obj.w__dict__ is None
        return obj

    def test_setgetdel_dictvalue(self):
        obj = self.make_obj()
        assert obj.getdictvalue(self.fakespace, "hello") == 1
        assert obj.getdictvalue(self.fakespace, "world") == 2
        assert obj.getdictvalue(self.fakespace, "bla") is None
        assert not obj.deldictvalue(self.fakespace, "bla")
        obj.deldictvalue(self.fakespace, "world")
        assert obj.getdictvalue(self.fakespace, "world") is None
        obj.deldictvalue(self.fakespace, "hello")
        assert obj.getdictvalue(self.fakespace, "hello") is None


    def test_getdict(self):
        obj = self.make_obj()
        w_dict = obj.getdict()
        assert obj.getdict() is w_dict # always get the same dict
        assert obj.w__dict__ is w_dict

        assert w_dict.getitem("hello") == 1
        assert w_dict.getitem("world") == 2
        w_dict.setitem("hello", 4)
        w_dict.setitem("world", 5)
        assert obj.getdictvalue(self.fakespace, "hello") == 4
        assert obj.getdictvalue(self.fakespace, "world") == 5

    def test_setdict(self):
        obj1 = self.make_obj()
        w_dict1 = obj1.getdict()
        obj2 = self.make_obj()
        w_dict2 = obj2.getdict()
        obj2.setdict(self.space, w_dict1)
        assert obj2.getdictvalue(self.fakespace, "hello") == 1
        assert obj2.getdictvalue(self.fakespace, "world") == 2
        obj1.setdictvalue(self.fakespace, "hello", 4)
        obj1.setdictvalue(self.fakespace, "world", 5)
        assert obj2.getdictvalue(self.fakespace, "hello") == 4
        assert obj2.getdictvalue(self.fakespace, "world") == 5
        assert w_dict2.getitem("hello") == 1
        assert w_dict2.getitem("world") == 2

    def test_setdict_keeps_previous_dict_working(self):
        obj1 = self.make_obj()
        w_dict1 = obj1.getdict()
        obj2 = self.make_obj()
        w_dict2 = obj2.getdict()
        w_dict2.setitem(4, 1) # devolve dict
        w_dict2.setitem(5, 2)
        obj2.setdict(self.space, w_dict1)
        assert obj2.getdictvalue(self.fakespace, "hello") == 1
        assert obj2.getdictvalue(self.fakespace, "world") == 2
        obj1.setdictvalue(self.fakespace, "hello", 4)
        obj1.setdictvalue(self.fakespace, "world", 5)
        assert obj2.getdictvalue(self.fakespace, "hello") == 4
        assert obj2.getdictvalue(self.fakespace, "world") == 5

    def test_setdict_devolves_existing_dict(self):
        obj1 = self.make_obj()
        w_dict1 = obj1.getdict()
        obj2 = self.make_obj()
        obj2.setdictvalue(self.fakespace, "hello", 6)
        obj2.setdictvalue(self.fakespace, "world", 7)
        w_dict2 = obj2.getdict()
        obj2.setdict(self.space, w_dict1)
        assert w_dict2.getitem("hello") == 6
        assert w_dict2.getitem("world") == 7
        assert obj2.getdictvalue(self.fakespace, "hello") == 1
        assert obj2.getdictvalue(self.fakespace, "world") == 2
        obj1.setdictvalue(self.fakespace, "hello", 4)
        obj1.setdictvalue(self.fakespace, "world", 5)
        assert obj2.getdictvalue(self.fakespace, "hello") == 4
        assert obj2.getdictvalue(self.fakespace, "world") == 5

    def test_dict_devolves_via_dict(self):
        obj = self.make_obj()
        w_dict = obj.getdict()
        w_dict.setitem(4, 1)
        w_dict.setitem(5, 2)
        assert dict(w_dict.r_dict_content) == {4: 1, 5: 2, "hello": 1, "world": 2}
        assert obj.getdictvalue(self.fakespace, "hello") == 1
        assert obj.getdictvalue(self.fakespace, "world") == 2
        assert obj.getdictvalue(self.fakespace, 4) == 1
        assert obj.getdictvalue(self.fakespace, 5) == 2
        obj.deldictvalue(self.fakespace, "world")
        assert obj.getdictvalue(self.fakespace, "world") is None
        obj.deldictvalue(self.fakespace, "hello")
        assert obj.getdictvalue(self.fakespace, "hello") is None


class TestMixinShared(TestMixin):
    Mixin = make_inlinedict_mixin(SharedDictImplementation, "structure")
    class FakeObject(Mixin):
        def user_setup_slots(self, nslots):
            pass

class TestIndirectDict(BaseTestRDictImplementation):
    Mixin = make_inlinedict_mixin(StrDictImplementation, "content")
    class FakeObject(Mixin):
        def user_setup_slots(self, nslots):
            pass

    def get_impl(self):
        obj = self.FakeObject()
        obj.user_setup(self.fakespace, FakeSubtype)
        return obj.getdict()


class TestIndirectDictShared(TestIndirectDict):
    Mixin = make_inlinedict_mixin(SharedDictImplementation, "structure")
    class FakeObject(Mixin):
        def user_setup_slots(self, nslots):
            pass




class TestInlineDict(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withinlineddict": True})

    def test_simple(self):
        w_a = self.space.appexec([], """():
            class A(object):
                pass
            a = A()
            a.x = 12
            a.y = 13
            return a
        """)
        assert w_a.w__dict__ is None
        assert self.space.int_w(w_a.content['x']) == 12
        assert self.space.int_w(w_a.content['y']) == 13
