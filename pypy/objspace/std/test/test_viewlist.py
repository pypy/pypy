import py
from pypy.conftest import gettestobjspace
from pypy.interpreter.error import OperationError


class TestViewList:

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withmultilist" : True})

    def get_list(self, ctx):
        space = self.space
        l_w = [space.wrap(i) for i in (1, 2, 3)]
        def get(space, context, i):
            assert context is ctx
            return l_w[i]
        def set(space, context, i, what):
            assert context is ctx
        def app(space, context, what):
            assert context is ctx
            l_w.append(what)
        def delete(space, context, i):
            assert context is ctx
            raise OperationError(space.w_OSError, space.wrap("can't do that.."))
        def length(space, context):
            return len(l_w)
        return space.newviewlist(ctx, get, set, delete, app, length)

    def test_simple_operations(self):
        space = self.space
        ctx = object()
        w_list = self.get_list(ctx)
        w_0, w_1, w_2, w_3 = [space.wrap(i) for i in range(4)]
        assert space.eq_w(space.getitem(w_list, w_0), w_1)
        assert space.eq_w(space.getitem(w_list, w_1), w_2)
        assert space.eq_w(space.getitem(w_list, w_2), w_3)
        assert space.eq_w(space.len(w_list), w_3)
        exc = py.test.raises(OperationError, space.getitem, w_list, w_3).value
        assert exc.match(space, space.w_IndexError)
        exc = py.test.raises(OperationError, space.delitem, w_list, w_1).value
        assert exc.match(space, space.w_OSError)

    def test_setitem(self):
        space = self.space
        ctx = object()
        w_list = self.get_list(ctx)
        space.setitem(w_list, space.wrap(2), space.wrap(23))
        # Our test viewlist doesn't do anything for setting.
        assert space.eq_w(space.getitem(w_list, space.wrap(2)), space.wrap(3))
        w_4 = space.wrap(4)
        exc = py.test.raises(OperationError, space.setitem, w_list, w_4, w_4)
        exc = exc.value
        assert exc.match(space, space.w_IndexError)

    def test_length(self):
        space = self.space
        w_l = self.get_list(object())
        assert space.int_w(space.len(w_l)) == 3

    def test_add(self):
        space = self.space
        ctx = object()
        w_l1 = self.get_list(ctx)
        w_l2 = self.get_list(ctx)
        w_added = space.add(w_l1, w_l2)
        unwrapped = [space.int_w(w_v) for w_v in space.viewiterable(w_added)]
        assert unwrapped == [1, 2, 3]*2

    def test_append(self):
        space = self.space
        w_list = self.get_list(object())
        w_app = space.getattr(w_list, space.wrap("append"))
        space.call_function(w_app, space.wrap(4))
        assert space.int_w(space.len(w_list)) == 4
        assert space.eq_w(space.getitem(w_list, space.wrap(3)), space.wrap(4))

    def test_extend(self):
        space = self.space
        w_list = self.get_list(object())
        w_a = space.wrap("a")
        w_b = space.wrap("b")
        w_new = space.newlist([w_a, w_b])
        space.call_method(w_list, "extend", w_new)
        assert space.int_w(space.len(w_list)) == 5
        assert space.eq_w(space.getitem(w_list, space.wrap(3)), w_a)
        assert space.eq_w(space.getitem(w_list, space.wrap(4)), w_b)
