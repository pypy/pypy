
class AppTestBasic:
    spaceconfig = dict(usemodules=['_collections'])

    def test_ordereddict_present(self):
        from _collections import OrderedDict
        assert issubclass(OrderedDict, dict)
        assert hasattr(OrderedDict, 'move_to_end')

    def test_recursive_repr(self):
        from _collections import OrderedDict
        d = OrderedDict()
        d[1] = d
        assert repr(d) == 'OrderedDict([(1, ...)])'

    def test_subclass(self):
        from _collections import OrderedDict
        class MyODict(OrderedDict):
            def __setitem__(self, key, value):
                super().__setitem__(key, 42)
        d = MyODict(x=1)
        assert d['x'] == 42
        d.update({'y': 2})
        assert d['y'] == 42
