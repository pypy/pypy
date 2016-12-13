from pypy.module.cpyext.test.test_api import BaseApiTest
from rpython.rtyper.lltypesystem import rffi


class TestModuleObject(BaseApiTest):
    def test_module_getname(self, space, api):
        w_sys = space.wrap(space.sys)
        p = api.PyModule_GetName(w_sys)
        assert rffi.charp2str(p) == 'sys'
        p2 = api.PyModule_GetName(w_sys)
        assert p2 == p
        self.raises(space, api, SystemError, api.PyModule_GetName, space.w_True)
