import pytest
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.modsupport import PyModule_New, PyModule_GetName
from pypy.module.cpyext.test.test_api import BaseApiTest
from rpython.rtyper.lltypesystem import rffi


class TestModuleObject(BaseApiTest):
    def test_module_new(self, space):
        with rffi.scoped_str2charp('testname') as buf:
            w_mod = PyModule_New(space, buf)
        assert space.eq_w(space.getattr(w_mod, space.newtext('__name__')),
                          space.newtext('testname'))

    def test_module_getname(self, space):
        w_sys = space.wrap(space.sys)
        p = PyModule_GetName(space, w_sys)
        assert rffi.charp2str(p) == 'sys'
        p2 = PyModule_GetName(space, w_sys)
        assert p2 == p
        with pytest.raises(OperationError) as excinfo:
            PyModule_GetName(space, space.w_True)
        assert excinfo.value.w_type is space.w_SystemError
