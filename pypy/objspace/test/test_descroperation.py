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
        oldlookup = space.lookup
        def lookup(obj, name):
            if name == "iter":
                return None
            return oldlookup(obj, name)
        monkeypatch.setattr(space, "lookup", lookup)
        w_iter = space.iter(w_l)
        w_first = space.next(w_iter)
        assert space.int_w(w_first) == 1

    def test_shortcut_binop(self, monkeypatch, space):
        w_x = space.newutf8('abc', 3)
        w_y = space.newutf8('def', 3)
        monkeypatch.setattr(space, "lookup", None)
        assert space.utf8_w(space.add(w_x, w_y)) == 'abcdef'

    def test_shortcut_binop_not_implemented(self, space):
        from pypy.interpreter.error import OperationError
        w_x = space.newutf8('abc', 3)
        w_y = space.newutf8('def', 3)
        with raises(OperationError):
            assert space.utf8_w(space.mul(w_x, w_y)) == 'abcdef'

    def test_shortcut_eq(self, monkeypatch, space):
        w_x = space.newutf8('abc', 3)
        w_y = space.newutf8('def', 3)
        monkeypatch.setattr(space, "lookup", None)
        assert not space.eq_w(w_x, w_y)

    def test_shortcut_dictiter(self, monkeypatch, space):
        w_x = space.wrap({'a': 1})
        oldlookup = space.lookup
        def lookup(obj, name):
            if name == "iter":
                return None
            return oldlookup(obj, name)
        monkeypatch.setattr(space, "lookup", lookup)
        w_iter = space.iter(w_x)
        w_first = space.next(w_iter)
        assert space.utf8_w(w_first) == 'a'

    def test_shortcut_str_getitem(self, monkeypatch, space):
        w_x = space.newbytes('abc')
        monkeypatch.setattr(space, "lookup", None)
        w_first = space.getitem(w_x, space.newint(0))
        assert space.bytes_w(w_first) == 'a'

    def test_no_shortcut_classobj(self):
        from pypy.module.__builtin__.interp_classobj import W_InstanceObject, W_ClassObject
        for key in W_InstanceObject.__dict__.keys() + W_ClassObject.__dict__.keys():
            assert not key.startswith("shortcut_")

    def test_shortcut_generatoriterator(self):
        from pypy.interpreter.generator import GeneratorIterator
        assert 'shortcut_next' in GeneratorIterator.__dict__

    def test_shortcut_len(self, monkeypatch, space):
        monkeypatch.setattr(space, "lookup", None)
        for val in "abc", [1, 2, 3], {'a', 'b', 'c'}, dict(a=1, b=2, d=3):
            assert space.len_w(space.wrap(val)) == 3

