import pytest
from pypy.module.hpy_universal import handles
from pypy.module.hpy_universal.handles import HandleManager

class FakeSpace(object):
    def __init__(self):
        self._cache = {}
    
    def fromcache(self, cls):
        if cls not in self._cache:
            self._cache[cls] = cls(self)
        return self._cache[cls]

    def __getattr__(self, name):
        return '<fakespace.%s>' % name

@pytest.fixture
def fakespace():
    return FakeSpace()

def test_fakespace(fakespace):
    assert fakespace.w_ValueError == '<fakespace.w_ValueError>'
    def x(space):
        return object()
    assert fakespace.fromcache(x) is fakespace.fromcache(x)

class TestHandleManager(object):

    def test_first_handle_is_not_zero(self, fakespace):
        mgr = HandleManager(fakespace)
        h = mgr.new('hello')
        assert h > 0

    def test_new(self, fakespace):
        mgr = HandleManager(fakespace)
        h = mgr.new('hello')
        assert mgr.handles_w[h] == 'hello'

    def test_close(self, fakespace):
        mgr = HandleManager(fakespace)
        h = mgr.new('hello')
        assert mgr.close(h) is None
        assert mgr.handles_w[h] is None

    def test_deref(self, fakespace):
        mgr = HandleManager(fakespace)
        h = mgr.new('hello')
        assert mgr.deref(h) == 'hello'     # 'hello' is a fake W_Root
        assert mgr.deref(h) == 'hello'

    def test_consume(self, fakespace):
        mgr = HandleManager(fakespace)
        h = mgr.new('hello')
        assert mgr.consume(h) == 'hello'
        assert mgr.handles_w[h] is None

    def test_freelist(self, fakespace):
        mgr = HandleManager(fakespace)
        h0 = mgr.new('hello')
        h1 = mgr.new('world')
        assert mgr.consume(h0) == 'hello'
        assert mgr.free_list == [h0]
        h2 = mgr.new('hello2')
        assert h2 == h0
        assert mgr.free_list == []

    def test_dup(self, fakespace):
        mgr = HandleManager(fakespace)
        h0 = mgr.new('hello')
        h1 = mgr.dup(h0)
        assert h1 != h0
        assert mgr.consume(h0) == mgr.consume(h1) == 'hello'

def test_using(fakespace):
    mgr = fakespace.fromcache(HandleManager)
    with handles.using(fakespace, 'hello') as h:
        assert mgr.handles_w[h] == 'hello'
    assert mgr.handles_w[h] is None
