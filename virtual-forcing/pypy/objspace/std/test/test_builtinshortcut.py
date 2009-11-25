from pypy.objspace.std.test import test_userobject
from pypy.objspace.std.test import test_setobject
from pypy.objspace.std.test import test_stringobject

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

    def test_inplace_methods(self):
        assert '__iadd__' not in int.__dict__
        assert '__iadd__' not in float.__dict__
        x = 5
        x += 6.5
        assert x == 11.5

    def test_inplace_user_subclasses(self):
        class I(int): pass
        class F(float): pass
        x = I(5)
        x += F(6.5)
        assert x == 11.5
        assert type(x) is float

    def test_inplace_override(self):
        class I(int):
            def __iadd__(self, other):
                return 'foo'
        x = I(5)
        x += 6
        assert x == 'foo'
        x = I(5)
        x += 6.5
        assert x == 'foo'
        assert 5 + 6.5 == 11.5

    def test_unicode_string_compares(self):
        assert u'a' == 'a'
        assert 'a' == u'a'
        assert not u'a' == 'b'
        assert not 'a'  == u'b'
        assert u'a' != 'b'
        assert 'a'  != u'b'
        assert not (u'a' == 5)
        assert u'a' != 5
        assert u'a' < 5 or u'a' > 5

        s = chr(128)
        u = unichr(128)
        assert not s == u # UnicodeWarning
        assert s != u
        assert not u == s
        assert u != s
   

class AppTestSet(test_setobject.AppTestAppSetTest):
    # this tests tons of funny comparison combinations that can easily go wrong
    def setup_class(cls):
        from pypy import conftest
        cls.space = conftest.gettestobjspace(**WITH_BUILTINSHORTCUT)

class AppTestString(test_stringobject.AppTestStringObject):
    def setup_class(cls):
        from pypy import conftest
        cls.space = conftest.gettestobjspace(**WITH_BUILTINSHORTCUT)
