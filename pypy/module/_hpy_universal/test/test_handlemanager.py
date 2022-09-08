import pytest
from pypy.module._hpy_universal.handlemanager import HandleReleaseCallback
from pypy.module._hpy_universal.state import State
# import for the side effect of adding the API functions
from pypy.module._hpy_universal import interp_hpy
from pypy.module._hpy_universal import llapi

class Config(object):
    def __init__(self, space):
        self.objspace = space
        self.translating = True

class FakeSpace(object):
    def __init__(self):
        self._cache = {}
        self.config = Config(self)

    def fromcache(self, cls):
        if cls not in self._cache:
            self._cache[cls] = cls(self)
        return self._cache[cls]

    def call(self, w_func, w_args, w_kw):
        # This is just enough for the debug closing on_invalid_handle callback
        if w_args is None and w_kw is None:
            return w_func()
        else:
            raise RuntimeError('space.call not fully implemented')

    def __getattr__(self, name):
        return '<fakespace.%s>' % name

@pytest.fixture(scope="module")
def fakespace():
    return FakeSpace()

def test_fakespace(fakespace):
    assert fakespace.w_ValueError == '<fakespace.w_ValueError>'
    def x(space):
        return object()
    assert fakespace.fromcache(x) is fakespace.fromcache(x)

def callback():
    # "trick" the debug context into not raising a fatal error when hitting a
    # closed handle
    pass

@pytest.fixture(scope="module", params=['universal', 'debug'])
def mgr(fakespace, request):
    # Do everything in interp_hpy.startup
    from pypy.module._hpy_universal.interp_type import setup_hpy_storage
    state = fakespace.fromcache(State)
    state.setup(fakespace)
    setup_hpy_storage()
    # end of interp_hpy.startup
    debug = request.param == 'debug'
    ret = state.get_handle_manager(debug)
    return ret
    

class TestHandleManager(object):

    def test_first_handle_is_not_zero(self, mgr):
        h = mgr.new('hello')
        assert h > 0

    def test_new(self, mgr):
        h = mgr.new('hello')
        assert mgr.deref(h) == 'hello'

    def test_close(self, mgr):
        h = mgr.new('hello')
        assert mgr.close(h) is None
        if not mgr.is_debug:
            # will crash PyPy on purpose in debug mode
            assert mgr.deref(h) is None

    def test_deref(self, mgr):
        h = mgr.new('hello')
        assert mgr.deref(h) == 'hello'     # 'hello' is a fake W_Root
        assert mgr.deref(h) == 'hello'

    def test_consume(self, mgr):
        h = mgr.new('hello')
        assert mgr.consume(h) == 'hello'
        if not mgr.is_debug:
            # will crash PyPy on purpose in debug mode
            assert mgr.deref(h) is None

    def test_freelist(self, mgr):
        if mgr.is_debug:
            pytest.skip('only for HandleManager')
        h0 = mgr.new('hello')
        h1 = mgr.new('world')
        assert mgr.consume(h0) == 'hello'
        assert mgr.free_list == [h0]
        h2 = mgr.new('hello2')
        assert h2 == h0
        assert mgr.free_list == []

    def test_dup(self, mgr):
        h0 = mgr.new('hello')
        h1 = mgr.dup(h0)
        assert h1 != h0
        assert mgr.consume(h0) == mgr.consume(h1) == 'hello'


class TestReleaseCallback(object):

    class MyCallback(HandleReleaseCallback):
        def __init__(self, seen, data):
            self.seen = seen
            self.data = data
        def release(self, h, obj):
            self.seen.append((h, obj, self.data))

    def test_callback(self, mgr):
        seen = []
        h0 = mgr.new('hello')
        h1 = mgr.dup(h0)
        h2 = mgr.dup(h0)
        mgr.attach_release_callback(h0, self.MyCallback(seen, 'foo'))
        mgr.attach_release_callback(h1, self.MyCallback(seen, 'bar'))
        assert seen == []
        #
        mgr.close(h1)
        assert seen == [(h1, 'hello', 'bar')]
        #
        mgr.close(h2)
        assert seen == [(h1, 'hello', 'bar')]
        #
        mgr.close(h0)
        assert seen == [(h1, 'hello', 'bar'),
                        (h0, 'hello', 'foo')]

    def test_clear(self, mgr):
        seen = []
        h0 = mgr.new('hello')
        mgr.attach_release_callback(h0, self.MyCallback(seen, 'foo'))
        mgr.close(h0)
        assert seen == [(h0, 'hello', 'foo')]
        #
        # check that the releaser array is cleared when we close the handle
        # and that we don't run the releaser for a wrong object
        h1 = mgr.new('world')
        if not mgr.is_debug:
            assert h1 == h0
        mgr.close(h1)
        assert seen == [(h0, 'hello', 'foo')]

    def test_multiple_releasers(self, mgr):
        seen = []
        h0 = mgr.new('hello')
        mgr.attach_release_callback(h0, self.MyCallback(seen, 'foo'))
        mgr.attach_release_callback(h0, self.MyCallback(seen, 'bar'))
        mgr.close(h0)
        assert seen == [(h0, 'hello', 'foo'),
                        (h0, 'hello', 'bar')]



class TestUsing(object):

    def test_simple(self, mgr):
        with mgr.using('hello') as h:
            assert mgr.deref(h) == 'hello'
        if not mgr.is_debug:
            # will crash PyPy on purpose in debug mode
            assert mgr.deref(h) is None

    def test_multiple_handles(self, mgr):
        with mgr.using('hello', 'world', 'foo') as (h1, h2, h3):
            assert mgr.deref(h1) == 'hello'
            assert mgr.deref(h2) == 'world'
            assert mgr.deref(h3) == 'foo'
        if not mgr.is_debug:
            # will crash PyPy on purpose in debug mode
            assert mgr.deref(h1) is None
            assert mgr.deref(h2) is None
            assert mgr.deref(h3) is None
