class Test_DescrOperation:

    def test_nonzero(self):
        space = self.space
        assert space.nonzero(space.w_True) is space.w_True
        assert space.nonzero(space.w_False) is space.w_False
        assert space.nonzero(space.wrap(42)) is space.w_True
        assert space.nonzero(space.wrap(0)) is space.w_False
        l = space.newlist([])
        assert space.nonzero(l) is space.w_False
        space.call_method(l, 'append', space.w_False)
        assert space.nonzero(l) is space.w_True

    def test_isinstance_and_issubtype_ignore_special(self):
        space = self.space
        w_tup = space.appexec((), """():
        class Meta(type):
            def __subclasscheck__(mcls, cls):
                return False
        class Base:
            __metaclass__ = Meta
        class Sub(Base):
            pass
        return Base, Sub""")
        w_base, w_sub = space.unpackiterable(w_tup)
        assert space.issubtype_w(w_sub, w_base)
        w_inst = space.call_function(w_sub)
        assert space.isinstance_w(w_inst, w_base)

    def test_shortcut(self, monkeypatch, space):
        w_l = space.wrap([1, 2, 3, 4])
        monkeypatch.setattr(space, "lookup", None)
        w_iter = space.iter(w_l)
        w_first = space.next(w_iter)
        assert space.int_w(w_first) == 1
