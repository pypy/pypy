

class AppTestHashtable:
    spaceconfig = dict(usemodules=['_stm'])

    def test_simple(self):
        import _stm
        h = _stm.hashtable()
        h[42+65536] = "bar"
        raises(KeyError, "h[42]")
        h[42] = "foo"
        assert h[42] == "foo"
        del h[42]
        raises(KeyError, "h[42]")
        assert h[42+65536] == "bar"
