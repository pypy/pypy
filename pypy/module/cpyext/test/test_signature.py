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
        assert str(info.value) == "unreachable: unexpected METH_TYPED signature", str(info.value)
