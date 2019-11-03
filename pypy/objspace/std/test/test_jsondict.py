
class AppTest(object):
    spaceconfig = {"objspace.usemodules._pypyjson": True}

    def test_check_strategy(self):
        import __pypy__
        import _pypyjson

        d = _pypyjson.loads('{"a": 1}')
        assert __pypy__.strategy(d) == "JsonDictStrategy"
        d = _pypyjson.loads('{}')
        assert __pypy__.strategy(d) == "EmptyDictStrategy"

    def test_simple(self):
        import __pypy__
        import _pypyjson

        d = _pypyjson.loads('{"a": 1, "b": "x"}')
        assert len(d) == 2
        assert d[u"a"] == 1
        assert d[u"b"] == u"x"
        assert u"c" not in d

        d[u"a"] = 5
        assert d[u"a"] == 5
        assert __pypy__.strategy(d) == "JsonDictStrategy"

        # devolve it
        assert not 1 in d
        assert __pypy__.strategy(d) == "UnicodeDictStrategy"
        assert len(d) == 2
        assert d[u"a"] == 5
        assert d[u"b"] == u"x"
        assert u"c" not in d

    def test_setdefault(self):
        import __pypy__
        import _pypyjson

        d = _pypyjson.loads('{"a": 1, "b": "x"}')
        assert d.setdefault(u"a", "blub") == 1
        d.setdefault(u"x", 23)
        assert __pypy__.strategy(d) == "UnicodeDictStrategy"
        assert len(d) == 3
        assert d == {u"a": 1, u"b": "x", u"x": 23}

    def test_delitem(self):
        import __pypy__
        import _pypyjson

        d = _pypyjson.loads('{"a": 1, "b": "x"}')
        del d[u"a"]
        assert __pypy__.strategy(d) == "UnicodeDictStrategy"
        assert len(d) == 1
        assert d == {u"b": "x"}

    def test_popitem(self):
        import __pypy__
        import _pypyjson

        d = _pypyjson.loads('{"a": 1, "b": "x"}')
        k, v = d.popitem()
        assert __pypy__.strategy(d) == "UnicodeDictStrategy"
        if k == u"a":
            assert v == 1
            assert len(d) == 1
            assert d == {u"b": "x"}
        else:
            assert v == u"x"
            assert len(d) == 1
            assert d == {u"a": 1}

    def test_keys_value_items(self):
        import _pypyjson

        d = _pypyjson.loads('{"a": 1, "b": "x"}')
        assert d.keys() == [u"a", u"b"]
        assert d.values() == [1, u"x"]
        assert d.items() == [(u"a", 1), (u"b", u"x")]

    def test_iter_keys_value_items(self):
        import _pypyjson

        d = _pypyjson.loads('{"a": 1, "b": "x"}')
        assert list(d.iterkeys()) == [u"a", u"b"]
        assert list(d.itervalues()) == [1, u"x"]
        assert list(d.iteritems()) == [(u"a", 1), (u"b", u"x")]

    def test_dict_order_retained_when_switching_strategies(self):
        import _pypyjson
        import __pypy__
        d = _pypyjson.loads('{"a": 1, "b": "x"}')
        assert list(d) == [u"a", u"b"]
        # devolve
        assert not 1 in d
        assert __pypy__.strategy(d) == "UnicodeDictStrategy"
        assert list(d) == [u"a", u"b"]

    def test_bug(self):
        import _pypyjson
        a =  """
        {
          "top": {
            "k": "8",
            "k": "8",
            "boom": 1
          }
        }
        """
        d = _pypyjson.loads(a)
        str(d)
        repr(d)


class TestJsonDictBlockedJsonMap(object):
    def make_jsondict(self):
        from pypy.module._pypyjson import interp_decoder
        from pypy.objspace.std.jsondict import from_values_and_jsonmap
        space = self.space
        w_a = self.space.newutf8("a", 1)
        w_b = self.space.newutf8("b", 1)
        base = interp_decoder.Terminator(space)
        m1 = base.get_next(w_a, 'a"', 0, 2, base)
        m2 = m1.get_next(w_b, 'b"', 0, 2, base)

        w_d = from_values_and_jsonmap(space, [w_a, w_b], m2)
        return base, m2, w_d, w_a, w_b

    def test_getitem(self):
        space = self.space
        base, m2, w_d, w_a, w_b = self.make_jsondict()
        assert space.getitem(w_d, w_a) is w_a
        assert space.getitem(w_d, w_b) is w_b

        m2.mark_blocked(base)
        # accessing a dict with a blocked strategy will switch to
        # UnicodeDictStrategy
        assert w_d.dstrategy is m2.strategy_instance
        assert space.getitem(w_d, w_a) is w_a
        assert space.getitem(w_d, w_b) is w_b
        assert w_d.dstrategy is not m2.strategy_instance

    def test_setitem(self):
        space = self.space
        base, m2, w_d, w_a, w_b = self.make_jsondict()
        space.setitem(w_d, w_a, w_b)
        space.setitem(w_d, w_b, w_a)

        m2.mark_blocked(base)
        assert w_d.dstrategy is m2.strategy_instance
        space.setitem(w_d, w_a, w_b)
        space.setitem(w_d, w_b, w_a)
        assert w_d.dstrategy is not m2.strategy_instance

    def test_len(self):
        space = self.space
        base, m2, w_d, w_a, w_b = self.make_jsondict()
        assert space.len_w(w_d) == 2

        m2.mark_blocked(base)
        assert w_d.dstrategy is m2.strategy_instance
        assert space.len_w(w_d) == 2
        assert w_d.dstrategy is not m2.strategy_instance

    def test_setdefault(self):
        base, m2, w_d, w_a, w_b = self.make_jsondict()
        assert w_d.setdefault(w_a, None) is w_a
        assert w_d.setdefault(w_b, None) is w_b

        m2.mark_blocked(base)
        assert w_d.dstrategy is m2.strategy_instance
        assert w_d.setdefault(w_a, None) is w_a
        assert w_d.setdefault(w_b, None) is w_b
        assert w_d.dstrategy is not m2.strategy_instance
