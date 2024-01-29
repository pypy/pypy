from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestSignature(AppTestCpythonExtensionBase):
    def test_import(self):
        module = self.import_module(name='signature')

    def test_call_inc(self):
        module = self.import_module(name='signature')
        result = module.inc(4)
        assert result == 5

    def test_call_inc_with_too_many_arguments_raises_type_error(self):
        module = self.import_module(name='signature')
        with raises(TypeError) as info:
            module.inc(4, 5)
        assert str(info.value) == "inc() takes exactly one argument (2 given)", str(info.value)

    def test_call_inc_with_wrong_argument_type_raises_type_error(self):
        module = self.import_module(name='signature')
        with raises(TypeError) as info:
            module.inc(4.5)
        assert str(info.value) == "expected integer, got float object", str(info.value)

    def test_call_inc_with_wrong_type_sig_raises_runtime_error(self):
        module = self.import_module(name='signature')
        with raises(RuntimeError) as info:
            module.wrong(1)
        assert str(info.value) == "unreachable: unexpected METH_O|METH_TYPED signature", str(info.value)

    def test_call_long_does_not_raise(self):
        module = self.import_module(name='signature')
        result = module.raise_long(8)
        assert result == 8

    def test_call_long_raises(self):
        module = self.import_module(name='signature')
        with raises(RuntimeError) as info:
            module.raise_long(123)
        assert str(info.value) == "got 123. raising"

    # double -> double -> double

    def test_call_add(self):
        module = self.import_module(name='signature')
        result = module.add(1.0, 2.0)
        assert result == 3.0

    def test_call_add_with_too_many_arguments_raises_type_error(self):
        module = self.import_module(name='signature')
        with raises(TypeError) as info:
            module.add(4.0, 5.0, 6.0)
        assert str(info.value) == "add expected 2 arguments but got 3", str(info.value)

    def test_call_add_with_wrong_argument_type_raises_type_error(self):
        module = self.import_module(name='signature')
        with raises(TypeError) as info:
            module.add(4, 5)
        assert str(info.value) == "add expected float but got int", str(info.value)

    def test_call_double_does_not_raise(self):
        module = self.import_module(name='signature')
        result = module.raise_double(1.0)
        assert result == 1.0

    def test_call_double_raises(self):
        module = self.import_module(name='signature')
        with raises(RuntimeError) as info:
            module.raise_double(0.0)
        assert str(info.value) == "got 0. raising"
