
from pypy.conftest import gettestobjspace
from pypy.module._rawffi.tracker import Tracker

class AppTestTracker:
    def setup_class(cls):
        Tracker.DO_TRACING = True
        space = gettestobjspace(usemodules=('_rawffi','struct'))
        cls.space = space

    def test_array(self):
        import _rawffi
        assert _rawffi._num_of_allocated_objects() == 0
        a = _rawffi.Array('c')(3)
        assert _rawffi._num_of_allocated_objects() == 1
        a.free()
        assert _rawffi._num_of_allocated_objects() == 0

    def test_structure(self):
        import _rawffi
        assert _rawffi._num_of_allocated_objects() == 0
        s = _rawffi.Structure([('a', 'i'), ('b', 'i')])()
        assert _rawffi._num_of_allocated_objects() == 1
        s.free()
        assert _rawffi._num_of_allocated_objects() == 0

    def teardown_class(cls):
        Tracker.DO_TRACING = False

