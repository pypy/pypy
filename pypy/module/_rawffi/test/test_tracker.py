
from pypy.conftest import gettestobjspace
from pypy.module._rawffi.tracker import Tracker

class AppTestTracker:
    def setup_class(cls):
        Tracker.DO_TRACING = True
        space = gettestobjspace(usemodules=('_rawffi','struct'))
        cls.space = space

    def test_array(self):
        import _rawffi
        oldnum = _rawffi._num_of_allocated_objects()
        a = _rawffi.Array('c')(3)
        assert _rawffi._num_of_allocated_objects() - oldnum == 1
        a.free()
        assert _rawffi._num_of_allocated_objects() - oldnum == 0

    def test_structure(self):
        import _rawffi
        oldnum = _rawffi._num_of_allocated_objects()
        s = _rawffi.Structure([('a', 'i'), ('b', 'i')])()
        assert _rawffi._num_of_allocated_objects() - oldnum == 1
        s.free()
        assert _rawffi._num_of_allocated_objects() - oldnum == 0

    def test_callback(self):
        import _rawffi
        oldnum = _rawffi._num_of_allocated_objects()
        c = _rawffi.CallbackPtr(lambda : 3, [], 'i')
        assert _rawffi._num_of_allocated_objects() - oldnum== 1
        c.free()
        assert _rawffi._num_of_allocated_objects() - oldnum== 0

    def teardown_class(cls):
        Tracker.DO_TRACING = False

