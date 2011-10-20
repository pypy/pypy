


class TestW_BoolObject:

    def setup_method(self,method):
        self.true = self.space.w_True
        self.false = self.space.w_False
        self.wrap = self.space.wrap

    def test_repr(self):
        assert self.space.eq_w(self.space.repr(self.true), self.wrap("True"))
        assert self.space.eq_w(self.space.repr(self.false), self.wrap("False"))
    
    def test_true(self):
        assert self.space.is_true(self.true)
        
    def test_false(self):
        assert not self.space.is_true(self.false)

    def test_uint_w(self):
        assert self.space.uint_w(self.true) == 1

    def test_rbigint_w(self):
        assert self.space.bigint_w(self.true)._digits == [1]
        
class AppTestAppBoolTest:
    def test_bool_callable(self):
        assert True == bool(1)
        assert False == bool(0)
        assert False == bool()

    def test_bool_string(self):
        assert "True" == str(True)
        assert "False" == str(False)
        assert "True" == repr(True)
        assert "False" == repr(False)

    def test_bool_ops(self):
        assert True + True == 2
        assert False | False is False
        assert True | False is True
        assert True & True is True
        assert True ^ True is False
        assert False ^ False is False
        assert True ^ False is True

    def test_new(self):
        assert bool.__new__(bool, "hi") is True
        assert bool.__new__(bool, "") is False
        raises(TypeError, bool.__new__, int)
        raises(TypeError, bool.__new__, 42)

    def test_cant_subclass_bool(self):
        raises(TypeError, "class b(bool): pass")
