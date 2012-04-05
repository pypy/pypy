from pypy.objspace.std.iterobject import length_hint


class TestLengthHint:

    SIZE = 4
    ITEMS = range(SIZE)

    def _test_length_hint(self, w_obj):
        space = self.space
        assert length_hint(space, w_obj, 8) == self.SIZE

        w_iter = space.iter(w_obj)
        assert space.int_w(
            space.call_method(w_iter, '__length_hint__')) == self.SIZE
        assert length_hint(space, w_iter, 8) == self.SIZE

        space.next(w_iter)
        assert length_hint(space, w_iter, 8) == self.SIZE - 1

    def test_list(self):
        self._test_length_hint(self.space.newlist(self.ITEMS))

    def test_tuple(self):
        self._test_length_hint(self.space.newtuple(self.ITEMS))

    def test_reversed(self):
        space = self.space
        w_reversed = space.call_method(space.builtin, 'reversed',
                                       space.newlist(self.ITEMS))
        assert space.int_w(
            space.call_method(w_reversed, '__length_hint__')) == self.SIZE
        self._test_length_hint(w_reversed)

    def test_default(self):
        space = self.space
        assert length_hint(space, space.w_False, 3) == 3

    def test_exc(self):
        from pypy.interpreter.error import OperationError
        space = self.space
        w_foo = space.appexec([], """():
            class Foo:
                def __length_hint__(self):
                    1 / 0
            return Foo()
        """)
        try:
            assert length_hint(space, w_foo, 3)
        except OperationError, e:
            assert e.match(space, space.w_ZeroDivisionError)
        else:
            assert False, 'ZeroDivisionError expected'
