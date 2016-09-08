from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from rpython.rtyper.lltypesystem import rffi

class TestImport(BaseApiTest):
    def test_import(self, space, api):
        stat = api.PyImport_Import(space.wrap("stat"))
        assert stat
        assert space.getattr(stat, space.wrap("S_IMODE"))

    def test_addmodule(self, space, api):
        with rffi.scoped_str2charp("sys") as modname:
            w_sys = api.PyImport_AddModule(modname)
        assert w_sys is space.sys

        with rffi.scoped_str2charp("foobar") as modname:
            w_foobar = api.PyImport_AddModule(modname)
        assert space.str_w(space.getattr(w_foobar,
                                         space.wrap('__name__'))) == 'foobar'

    def test_getmoduledict(self, space, api):
        testmod = "_functools"
        w_pre_dict = api.PyImport_GetModuleDict()
        assert not space.contains_w(w_pre_dict, space.wrap(testmod))

        with rffi.scoped_str2charp(testmod) as modname:
            w_module = api.PyImport_ImportModule(modname)
            print w_module
            assert w_module

        w_dict = api.PyImport_GetModuleDict()
        assert space.contains_w(w_dict, space.wrap(testmod))

    def test_reload(self, space, api):
        stat = api.PyImport_Import(space.wrap("stat"))
        space.delattr(stat, space.wrap("S_IMODE"))
        stat = api.PyImport_ReloadModule(stat)
        assert space.getattr(stat, space.wrap("S_IMODE"))

class AppTestImportLogic(AppTestCpythonExtensionBase):
    def test_import_logic(self):
        import sys, os
        path = self.import_module(name='test_import_module', load_it=False)
        sys.path.append(os.path.dirname(path))
        import test_import_module
        assert test_import_module.TEST is None
