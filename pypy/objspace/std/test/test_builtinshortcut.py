from pypy.objspace.std.test import test_userobject
from pypy.objspace.std.test import test_set

WITH_BUILTINSHORTCUT = {'objspace.std.builtinshortcut': True}

class AppTestUserObject(test_userobject.AppTestUserObject):
    OPTIONS = WITH_BUILTINSHORTCUT

class AppTestWithMultiMethodVersion2(test_userobject.AppTestWithMultiMethodVersion2):
    OPTIONS = WITH_BUILTINSHORTCUT

class AppTestBug:
    def setup_class(cls):
        from pypy import conftest
        cls.space = conftest.gettestobjspace(**WITH_BUILTINSHORTCUT)

    def test_frozen_subtype(self):
        class S(set): pass
        assert set("abc") == S("abc")
        assert S("abc") == set("abc")
        class F(frozenset): pass
        assert frozenset("abc") == F("abc")
        assert F("abc") == frozenset("abc")

        assert S("abc") in set([frozenset("abc")])
        assert F("abc") in set([frozenset("abc")])

        s = set([frozenset("abc")])
        s.discard(S("abc"))
        assert not s

        s = set([frozenset("abc")])
        s.discard(F("abc"))
        assert not s

class AppTestSet(test_set.AppTestAppSetTest):
    # this tests tons of funny comparison combinations that can easily go wrong
    def setup_class(cls):
        from pypy import conftest
        cls.space = conftest.gettestobjspace(**WITH_BUILTINSHORTCUT)
