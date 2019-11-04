
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

    def test_append(self):
        from __pypy__ import newdictstructure
        s = newdictstructure([u"a"])
        s1 = s.append(u"b")
        assert s.append(u"b") is s1
        assert s1.instantiate_dict([1, 2]) == {u"a": 1, u"b": 2}
        with raises(ValueError):
            s.append(u"a")


class TestDictStructure(object):
    def test_append_and_transitions(self):
        from pypy.module._pypyjson.interp_decoder import Terminator
        m = Terminator(self.space)
        w_a = self.space.newutf8("a", 1)
        w_b = self.space.newutf8("b", 1)
        m1 = m.descr_append(self.space, w_a)
        m2 = m1.descr_append(self.space, w_b)
        count = m2.instantiation_count
        m1.descr_append(self.space, w_b)
        assert m2.instantiation_count == count + 1
