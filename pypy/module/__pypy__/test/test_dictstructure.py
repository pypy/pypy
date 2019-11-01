
class AppTestDictStructure(object):
    spaceconfig = dict(usemodules=['__pypy__', '_pypyjson'])

    def test_simple(self):
        from __pypy__ import newdictstructure, strategy
        m = newdictstructure([u"a", u"b", u"c"])
        assert m.last_key == u"c"
        assert m.previous.last_key == u"b"
        m2 = newdictstructure([u"a", u"b", u"c"])
        assert m2 is m
        d = m.instantiate_dict([1, 2, 3])
        assert d == {u"a": 1, u"b": 2, u"c": 3}
        assert strategy(d) == "JsonDictStrategy"

        with raises(ValueError):
            m.instantiate_dict([5])

        with raises(TypeError):
            newdictstructure([b"a"])


    def test_repr(self):
        from __pypy__ import newdictstructure, strategy
        m = newdictstructure([u"a"])
        assert repr(m) == "<DictStructure [u'a']>"

    def test_repeated_key(self):
        from __pypy__ import newdictstructure
        with raises(ValueError):
            newdictstructure([u"a", u"a"])
