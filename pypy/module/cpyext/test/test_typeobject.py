from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

import py
import sys

class AppTestTypeObject(AppTestCpythonExtensionBase):
    def test_typeobject(self):
        skip("In progress")
        import sys
        module = self.import_module(name='foo')
        assert 'foo' in sys.modules
        assert module.new().name == "Foo Example"
