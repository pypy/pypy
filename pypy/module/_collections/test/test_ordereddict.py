
class AppTestBasic:
    spaceconfig = dict(usemodules=['_collections'])

    def test_ordereddict_present(self):
        from _collections import OrderedDict
        assert issubclass(OrderedDict, dict)
        assert hasattr(OrderedDict, 'move_to_end')
